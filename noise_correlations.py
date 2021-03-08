# -*- coding: utf-8 -*-

"""

@author: bartulem

Calculate noise correlations.

"""

import os
import numpy as np
import scipy.io as sio
from numba import njit
from itertools import combinations
from scipy.ndimage import gaussian_filter1d
from sessions2load import Session
from select_clusters import ClusterFinder
from neural_activity import purge_spikes_beyond_tracking


def get_firing_rate(cl_activity, bin_size,
                    tracking_start, tracking_stop,
                    to_jitter=True, jitter_size=.005, shuffle_n=1000):
    fr_arr = np.zeros(int(np.ceil((tracking_stop-tracking_start)/bin_size)))
    jitter_arr = np.zeros((shuffle_n, fr_arr.shape[0]))
    if to_jitter:
        for sh in range(shuffle_n):
            jitter_spikes = cl_activity.copy() + ((2 * jitter_size * np.random.random(cl_activity.shape[0])) - jitter_size)
            jitter_spikes = jitter_spikes[jitter_spikes <= tracking_stop]
            jitter_arr[sh, np.round(jitter_spikes/bin_size).astype(np.int32)] += 1
            if sh == 0:
                fr_arr[np.round(cl_activity/bin_size).astype(np.int32)] += 1
    else:
        fr_arr[np.round(cl_activity/bin_size).astype(np.int32)] += 1
    return fr_arr, jitter_arr

@njit(parallel=False)
def cross_correlate(big_x, big_x_mean, small_y, small_y_mean):
    reshaped_x_mean = np.reshape(big_x_mean, (big_x.shape[0], 1))
    r_num = np.sum((big_x-reshaped_x_mean)*(small_y-small_y_mean), axis=1)
    r_den = np.sqrt(np.sum((big_x-reshaped_x_mean)**2, axis=1)*np.sum((small_y-small_y_mean)**2))
    r = r_num/r_den
    return r


class FunctionalConnectivity:

    def __init__(self, pkl_sessions_dir='', cluster_groups_dir='',
                 sp_profiles_csv='', pkl_file='', save_dir=''):
        self.pkl_sessions_dir = pkl_sessions_dir
        self.cluster_groups_dir = cluster_groups_dir
        self.sp_profiles_csv = sp_profiles_csv
        self.pkl_file = pkl_file
        self.save_dir=save_dir

    def noise_corr(self, **kwargs):
        """
        Description
        ----------
        This method calculates noise correlations for all clusters in a given session.
        ----------

        Parameters
        ----------
        **kwargs (dictionary)
        bin_size (float)
            The size of bins for binning spikes; defaults to .5 (ms).
        bin_num (float)
            The one-sided number of bins for the cross-correlogram; defaults to 40.
        std_smooth (float)
            The std. deviation of the gaussian smoothing kernel; defaults to 0.001 (ms).
        to_jitter (bool)
            To jitter or not to jitter spikes; defaults to True.
        num_jitters (int)
            The number of times to jitter data; defaults to 1000.
        jitter_size (int)
            The one-sided bound of the spike jitter; defaults to 0.005 (ms).
        area_filter (list / bool)
            Areas to be included, you can pick specific areas or
            general (A - auditory, M - motor, P - parietal, S - somatosensory, V - visual); defaults to True.
        cluster_type_filter (str / bool)
            Cluster type to be included: 'good' or 'mua'; defaults to True.
        profile_filter (str / bool)
            Profile to be included: 'RS' or 'FS'; defaults to True.
        sort_ch_num (bool)
            If True, sorts clusters by channel number; defaults to False.
        combo_idx (int)
            Index of combination of choice; defaults to 0.
        ----------

        Returns
        ----------
        noise_corrs (.mat file)
            .mat files containing cross-correlations of data/jitters.
        ----------
        """

        bin_size = kwargs['bin_size'] if 'bin_size' in kwargs.keys() and type(kwargs['bin_size']) == float else .0005
        bin_num = kwargs['bin_num'] if 'bin_num' in kwargs.keys() and type(kwargs['bin_num']) == int else 40
        smooth_fr = kwargs['smooth_fr'] if 'smooth_fr' in kwargs.keys() and type(kwargs['smooth_fr']) == bool else False
        std_smooth = kwargs['std_smooth'] if 'std_smooth' in kwargs.keys() and type(kwargs['std_smooth']) == float else .001
        to_jitter = kwargs['to_jitter'] if 'to_jitter' in kwargs.keys() and type(kwargs['to_jitter']) == bool else True
        num_jitters = kwargs['num_jitters'] if 'num_jitters' in kwargs.keys() and type(kwargs['num_jitters']) == int else 1000
        jitter_size = kwargs['jitter_size'] if 'jitter_size' in kwargs.keys() and type(kwargs['jitter_size']) == float else .005
        area_filter = kwargs['area_filter'] if 'area_filter' in kwargs.keys() and type(kwargs['area_filter']) == list else True
        cluster_type_filter = kwargs['cluster_type_filter'] if 'cluster_type_filter' in kwargs.keys() and type(kwargs['cluster_type_filter']) == str else True
        profile_filter = kwargs['profile_filter'] if 'profile_filter' in kwargs.keys() and type(kwargs['profile_filter']) == str else True
        sort_ch_num = kwargs['sort_ch_num'] if 'sort_ch_num' in kwargs.keys() and type(kwargs['sort_ch_num']) == bool else False
        combo_idx = kwargs['combo_idx'] if 'combo_idx' in kwargs.keys() and type(kwargs['combo_idx']) == int else 0

        combo_num = list(range(0, 40186, 113))[combo_idx]

        cluster_list = ClusterFinder(session=f'{self.pkl_sessions_dir}{os.sep}{self.pkl_file}',
                                     cluster_groups_dir=self.cluster_groups_dir,
                                     sp_profiles_csv=self.sp_profiles_csv).get_desired_clusters(filter_by_area=area_filter,
                                                                                                filter_by_cluster_type=cluster_type_filter,
                                                                                                filter_by_spiking_profile=profile_filter,
                                                                                                sort_ch_num=sort_ch_num)

        # get spike data in seconds and tracking start and end time
        file_id, cluster_data = Session(session=f'{self.pkl_sessions_dir}{os.sep}{self.pkl_file}').data_loader(extract_clusters=cluster_list, extract_variables=['tracking_ts'])

        # get all combinations of clusters
        cl_combinations = list(combinations(cluster_data['cluster_spikes'].keys(), 2))

        # pick a combination
        combo_name = f'{cl_combinations[combo_num][0]}-{cl_combinations[combo_num][1]}'
        act1 = cluster_data['cluster_spikes'][cl_combinations[combo_num][0]]
        act2 = cluster_data['cluster_spikes'][cl_combinations[combo_num][1]]

        # eliminate spikes that happen prior to and post tracking
        act1 = purge_spikes_beyond_tracking(spike_train=act1, tracking_ts=cluster_data['tracking_ts'])
        act2 = purge_spikes_beyond_tracking(spike_train=act2, tracking_ts=cluster_data['tracking_ts'])

        # get firing rates
        if to_jitter:
            fr1, sh1 = get_firing_rate(cl_activity=act1, bin_size=bin_size,
                                       tracking_start=cluster_data['tracking_ts'][0]-cluster_data['tracking_ts'][0],
                                       tracking_stop=cluster_data['tracking_ts'][1]-cluster_data['tracking_ts'][0],
                                       jitter_size=jitter_size, shuffle_n=num_jitters)

            fr2, sh2 = get_firing_rate(cl_activity=act2, bin_size=bin_size,
                                       tracking_start=cluster_data['tracking_ts'][0]-cluster_data['tracking_ts'][0],
                                       tracking_stop=cluster_data['tracking_ts'][1]-cluster_data['tracking_ts'][0],
                                       jitter_size=jitter_size, shuffle_n=num_jitters)

            if smooth_fr:
                fr1 = gaussian_filter1d(input=fr1, sigma=int(round(std_smooth/bin_size)))
                sh1 = gaussian_filter1d(input=sh1, sigma=int(round(std_smooth/bin_size)), axis=1)
                fr2 = gaussian_filter1d(input=fr2, sigma=int(round(std_smooth/bin_size)))
                sh2 = gaussian_filter1d(input=sh2, sigma=int(round(std_smooth/bin_size)), axis=1)
        else:
            fr1, sh1 = get_firing_rate(cl_activity=act1, bin_size=bin_size,
                                       tracking_start=cluster_data['tracking_ts'][0]-cluster_data['tracking_ts'][0],
                                       tracking_stop=cluster_data['tracking_ts'][1]-cluster_data['tracking_ts'][0],
                                       to_jitter=False, shuffle_n=1)

            fr2, sh2 = get_firing_rate(cl_activity=act2, bin_size=bin_size,
                                       tracking_start=cluster_data['tracking_ts'][0]-cluster_data['tracking_ts'][0],
                                       tracking_stop=cluster_data['tracking_ts'][1]-cluster_data['tracking_ts'][0],
                                       to_jitter=False, shuffle_n=1)

            if smooth_fr:
                fr1 = gaussian_filter1d(input=fr1, sigma=int(round(std_smooth/bin_size)))
                fr2 = gaussian_filter1d(input=fr2, sigma=int(round(std_smooth/bin_size)))

        # cross-correlate
        all_bins = np.arange(-bin_num, bin_num+1, 1)
        fr1_shape = fr1.shape[0]
        y_start = int(round(bin_num))
        y_end = int(round(fr1_shape-bin_num))
        big_x = np.zeros((all_bins.shape[0], y_end-y_start))
        y = np.zeros(y_end-y_start)
        if to_jitter:
            sh_data = np.zeros((num_jitters, all_bins.shape[0]))
            for sh in range(num_jitters):
                big_x_sh = np.zeros((all_bins.shape[0], y_end-y_start))
                y_sh = np.zeros(y_end-y_start)
                for bin_idx, one_bin in enumerate(all_bins):
                    start_x = int(round(bin_num+one_bin))
                    end_x = int(round(fr1_shape-bin_num+one_bin))
                    if sh == 0:
                        big_x[bin_idx, :] = fr1[start_x:end_x]
                    big_x_sh[bin_idx, :] = sh1[sh, start_x:end_x]
                    if bin_idx == 0:
                        if sh == 0:
                            y = fr2[y_start:y_end]
                        y_sh = sh2[sh, y_start:y_end]
                if sh == 0:
                    data = cross_correlate(big_x=big_x,
                                           big_x_mean=big_x.mean(axis=1),
                                           small_y=y,
                                           small_y_mean=y.mean())
                sh_data[sh, :] = cross_correlate(big_x=big_x_sh,
                                                 big_x_mean=big_x_sh.mean(axis=1),
                                                 small_y=y_sh,
                                                 small_y_mean=y_sh.mean())
        else:
            for bin_idx, one_bin in enumerate(all_bins):
                start_x = int(round(bin_num+one_bin))
                end_x = int(round(fr1_shape-bin_num+one_bin))
                big_x[bin_idx, :] = fr1[start_x:end_x]
                if bin_idx == 0:
                    y = fr2[y_start:y_end]
            data = cross_correlate(big_x=big_x,
                                   big_x_mean=big_x.mean(axis=1),
                                   small_y=y,
                                   small_y_mean=y.mean())

        if to_jitter:
            sio.savemat(f'{self.save_dir}{os.sep}{combo_name}.mat', {'cross_corr': data, 'sh_corr': sh_data}, oned_as='column')
        else:
            sio.savemat(f'{self.save_dir}{os.sep}{combo_name}.mat', {'cross_corr': data}, oned_as='column')