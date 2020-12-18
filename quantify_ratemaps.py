# -*- coding: utf-8 -*-

"""

@author: bartulem

Gets (1) tuning peak locations, (2) occupancies, (3) computes inter-session stability

"""

import os
import sys
import numpy as np
from tqdm import tqdm
from select_clusters import ClusterFinder


class RatemapCharacteristics:

    areas_to_animals = {'CaPu': {'bruno': ['distal']},
                        'WhMa': {'bruno': ['distal']},
                        'S': {'bruno': ['distal'], 'roy': ['intermediate'], 'jacopo': ['intermediate'], 'crazyjoe': ['intermediate']},
                        'S1HL': {'bruno': ['distal'], 'roy': ['intermediate'], 'jacopo': ['intermediate'], 'crazyjoe': ['intermediate']},
                        'S1Tr': {'bruno': ['distal'], 'jacopo': ['intermediate'], 'crazyjoe': ['intermediate']},
                        'M': {'bruno': ['distal'], 'roy': ['distal', 'intermediate'], 'jacopo': ['distal', 'intermediate'], 'crazyjoe': ['distal', 'intermediate']},
                        'M1': {'bruno': ['distal'], 'roy': ['distal', 'intermediate'], 'jacopo': ['distal', 'intermediate'], 'crazyjoe': ['distal', 'intermediate']},
                        'M2': {'jacopo': ['distal'], 'crazyjoe': ['distal']},
                        'PPC': {'bruno': ['distal'], 'jacopo': ['intermediate']},
                        'A': {'frank': ['distal'], 'johnjohn': ['distal'], 'kavorka': ['distal']},
                        'A1': {'frank': ['distal'], 'johnjohn': ['distal'], 'kavorka': ['distal']},
                        'A2D': {'frank': ['distal'], 'johnjohn': ['distal'], 'kavorka': ['distal']},
                        'V': {'frank': ['distal', 'intermediate'], 'johnjohn': ['distal', 'intermediate'], 'kavorka': ['distal', 'intermediate']},
                        'V1': {'frank': ['distal', 'intermediate'], 'johnjohn': ['distal', 'intermediate'], 'kavorka': ['distal', 'intermediate']},
                        'V2M': {'frank': ['intermediate'], 'johnjohn': ['intermediate'], 'kavorka': ['intermediate']},
                        'V2L': {'frank': ['distal'], 'johnjohn': ['distal'], 'kavorka': ['distal']}}

    def __init__(self, ratemap_mat_dir='', pkl_sessions_dir='', area_filter='M', animal_filter=True, profile_filter=True,
                 session_id_filter='s1', session_type_filter=True, cluster_type_filter=True,
                 cluster_groups_dir='', sp_profiles_csv='', specific_date=None):
        if specific_date is None:
            specific_date = {'bruno': ['020520', '030520'],
                             'roy': True,
                             'jacopo': True,
                             'crazyjoe': True,
                             'frank': True,
                             'johnjohn': ['210520', '220520'],
                             'kavorka': True}
        self.ratemap_mat_dir = ratemap_mat_dir
        self.pkl_sessions_dir = pkl_sessions_dir
        self.area_filter = area_filter
        self.cluster_type_filter = cluster_type_filter
        self.profile_filter = profile_filter
        self.animal_filter = animal_filter
        self.session_id_filter = session_id_filter
        self.session_type_filter = session_type_filter
        self.specific_date = specific_date
        self.cluster_groups_dir = cluster_groups_dir
        self.sp_profiles_csv = sp_profiles_csv

    def file_finder(self, **kwargs):
        """
        Description
        ----------
        This method finds files of interest in the ratemap .mat file directory. There are
        two options: you can look for all files with certain characteristics (i.e. lights
        & s1) in only one recording session (seek_stability=False), or if you are further
        interested in computing stability measures, you look for files across two specified
        recording sessions (seek_stability=True).
        ----------

        Parameters
        ----------
        **kwargs (dictionary)
        area_filter (str)
            Area of interest; defaults to 'M'.
        animal_filter (bool / list)
            Animals to consider: defaults to True (considers all).
        cluster_type_filter (bool / str)
            Cluster type to be included: 'good' or 'mua'; defaults to True.
        profile_filter (str / bool)
            Profile to be included: 'RS' or 'FS'; defaults to True.
        session_id_filter (bool / str)
            The session number of interest; defaults to 's1'.
        session_type_filter (bool / str)
            The session type of interest; defaults to True.
        specific_date (dict)
            The date of interest (for animals that had recordings across days); defaults to True for most animals.
        seek_stability (bool)
            If True, looks for ratemap files across two desired sessions; defaults to False.
        session_2_type (str)
            The type of the session you want to measure stability for; defaults to 'light'.
        ----------

        Returns
        ----------
        essential_files (dict)
            The dictionary of all relevant .mat ratemap files (for max two relevant session types) for further analyses.
        ----------
        """

        seek_stability = kwargs['seek_stability'] if 'seek_stability' in kwargs.keys() and type(kwargs['seek_stability']) == bool else False
        session_2_type = kwargs['session_2_type'] if 'session_2_type' in kwargs.keys() and type(kwargs['session_2_type']) == str else 'light'

        # get clusters of interest
        cluster_dict = {}
        for animal in self.areas_to_animals[self.area_filter].keys():
            cluster_dict[animal] = {}
            for bank in self.areas_to_animals[self.area_filter][animal]:
                for pkl_file in os.listdir(self.pkl_sessions_dir):
                    if animal in pkl_file and bank in pkl_file and (self.session_id_filter is True or self.session_id_filter in pkl_file) \
                            and (self.session_type_filter is True or self.session_type_filter in pkl_file) \
                            and (self.specific_date[animal] is True or any(one_date in pkl_file for one_date in self.specific_date[animal])):
                        cluster_dict[animal][bank] = ClusterFinder(session=f'{self.pkl_sessions_dir}{os.sep}{pkl_file}',
                                                                   cluster_groups_dir=self.cluster_groups_dir,
                                                                   sp_profiles_csv=self.sp_profiles_csv).get_desired_clusters(filter_by_area=[self.area_filter],
                                                                                                                              filter_by_cluster_type=self.cluster_type_filter,
                                                                                                                              filter_by_spiking_profile=self.profile_filter)
                        break

        # collect relevant file names in a list
        essential_files = {'chosen_session_1': [], 'chosen_session_2': []}
        if os.path.exists(self.ratemap_mat_dir):
            for file_name in tqdm(os.listdir(self.ratemap_mat_dir), desc='Checking all ratemap files'):
                if (self.animal_filter is True or any(one_animal in file_name for one_animal in self.animal_filter)) \
                        and (self.session_id_filter is True or self.session_id_filter in file_name) \
                        and (self.session_type_filter is True or self.session_type_filter in file_name):
                    animal_id = [name for name in ClusterFinder.probe_site_areas.keys() if name in file_name][0]
                    if animal_id == 'bruno':
                        bank_id = 'distal'
                    else:
                        bank_id = [bank for bank in ['distal', 'intermediate'] if bank in file_name][0]
                    cluster_id = file_name[file_name.find('imec'):file_name.find('imec') + 18]
                    if (self.specific_date[animal_id] is True or any(one_date in file_name for one_date in self.specific_date[animal_id])) \
                            and animal_id in cluster_dict.keys() and bank_id in cluster_dict[animal_id].keys():
                        if cluster_id in cluster_dict[animal_id][bank_id]:
                            if not seek_stability:
                                essential_files['chosen_session_1'].append(file_name)
                            else:
                                for file_name_2 in os.listdir(self.ratemap_mat_dir):
                                    if file_name != file_name_2 and animal_id in file_name_2 and bank_id in file_name_2 and cluster_id in file_name_2 \
                                            and (self.specific_date[animal_id] is True or any(one_date in file_name_2 for one_date in self.specific_date[animal_id])) \
                                            and session_2_type in file_name_2:
                                        essential_files['chosen_session_1'].append(file_name)
                                        essential_files['chosen_session_2'].append(file_name_2)
                                        break
        else:
            print(f"Invalid location for ratemap directory {self.ratemap_mat_dir}. Please try again.")
            sys.exit()

        print(f"Search complete. Found {len(essential_files['chosen_session_1'])} valid cluster(s) in area {self.area_filter}.")

        return essential_files

    def tuning_peak_locations(self, **kwargs):
        """
        Description
        ----------
        This method finds bin centers where the peak 1D tuning curve firing rate resides.
        ----------

        Parameters
        ----------
        **kwargs (dictionary)
        area_filter (str)
            Area of interest; defaults to 'M'.
        ----------

        Returns
        ----------
        essential_files (dict)
            The dictionary of all relevant .mat ratemap files (for max two relevant session types) for further analyses.
        ----------
        """

        essential_files = self.file_finder()
        print(essential_files)

