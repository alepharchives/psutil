#!/usr/bin/env python
#
# $Id$
#
# Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""OSX platform implementation."""

import errno
import os
import sys

import _psutil_osx
import _psutil_posix
from psutil import _psposix
from psutil.error import AccessDenied, NoSuchProcess, TimeoutExpired
from psutil._compat import namedtuple
from psutil._common import *

__extra__all__ = []

# --- constants

NUM_CPUS = _psutil_osx.get_num_cpus()
BOOT_TIME = _psutil_osx.get_system_boot_time()
_TERMINAL_MAP = _psposix._get_terminal_map()
_cputimes_ntuple = namedtuple('cputimes', 'user nice system idle')

# --- functions

def phymem_usage():
    """Physical system memory as a (total, used, free) tuple."""
    total = _psutil_osx.get_total_phymem()
    free =  _psutil_osx.get_avail_phymem()
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return nt_sysmeminfo(total, used, free, percent)

def virtmem_usage():
    """Virtual system memory as a (total, used, free) tuple."""
    total = _psutil_osx.get_total_virtmem()
    free =  _psutil_osx.get_avail_virtmem()
    used = total - free
    percent = usage_percent(used, total, _round=1)
    return nt_sysmeminfo(total, used, free, percent)

def get_system_cpu_times():
    """Return system CPU times as a namedtuple."""
    user, nice, system, idle = _psutil_osx.get_system_cpu_times()
    return _cputimes_ntuple(user, nice, system, idle)

def get_system_per_cpu_times():
    """Return system CPU times as a named tuple"""
    ret = []
    for cpu_t in _psutil_osx.get_system_per_cpu_times():
        user, nice, system, idle = cpu_t
        item = _cputimes_ntuple(user, nice, system, idle)
        ret.append(item)
    return ret

def disk_partitions(all=False):
    retlist = []
    partitions = _psutil_osx.get_disk_partitions()
    for partition in partitions:
        device, mountpoint, fstype, opts = partition
        if device == 'none':
            device = ''
        if not all:
            if not os.path.isabs(device) \
            or not os.path.exists(device):
                continue
        ntuple = nt_partition(device, mountpoint, fstype, opts)
        retlist.append(ntuple)
    return retlist

def get_system_users():
    retlist = []
    rawlist = _psutil_osx.get_system_users()
    for item in rawlist:
        user, tty, hostname, tstamp = item
        if tty == '~':
            continue  # reboot or shutdown
        if not tstamp:
            continue
        nt = nt_user(user, tty or None, hostname or None, tstamp)
        retlist.append(nt)
    return retlist


get_pid_list = _psutil_osx.get_pid_list
pid_exists = _psposix.pid_exists
get_disk_usage = _psposix.get_disk_usage
network_io_counters = _psutil_osx.get_network_io_counters
disk_io_counters = _psutil_osx.get_disk_io_counters

# --- decorator

def wrap_exceptions(callable):
    """Call callable into a try/except clause so that if an
    OSError EPERM exception is raised we translate it into
    psutil.AccessDenied.
    """
    def wrapper(self, *args, **kwargs):
        try:
            return callable(self, *args, **kwargs)
        except OSError:
            err = sys.exc_info()[1]
            if err.errno == errno.ESRCH:
                raise NoSuchProcess(self.pid, self._process_name)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._process_name)
            raise
    return wrapper


_status_map = {
    _psutil_osx.SIDL : STATUS_IDLE,
    _psutil_osx.SRUN : STATUS_RUNNING,
    _psutil_osx.SSLEEP : STATUS_SLEEPING,
    _psutil_osx.SSTOP : STATUS_STOPPED,
    _psutil_osx.SZOMB : STATUS_ZOMBIE,
}

class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_process_name"]

    def __init__(self, pid):
        self.pid = pid
        self._process_name = None

    @wrap_exceptions
    def get_process_name(self):
        """Return process name as a string of limited len (15)."""
        return _psutil_osx.get_process_name(self.pid)

    @wrap_exceptions
    def get_process_exe(self):
        return _psutil_osx.get_process_exe(self.pid)

    @wrap_exceptions
    def get_process_cmdline(self):
        """Return process cmdline as a list of arguments."""
        if not pid_exists(self.pid):
            raise NoSuchProcess(self.pid, self._process_name)
        return _psutil_osx.get_process_cmdline(self.pid)

    @wrap_exceptions
    def get_process_ppid(self):
        """Return process parent pid."""
        return _psutil_osx.get_process_ppid(self.pid)

    @wrap_exceptions
    def get_process_cwd(self):
        return _psutil_osx.get_process_cwd(self.pid)

    @wrap_exceptions
    def get_process_uids(self):
        real, effective, saved = _psutil_osx.get_process_uids(self.pid)
        return nt_uids(real, effective, saved)

    @wrap_exceptions
    def get_process_gids(self):
        real, effective, saved = _psutil_osx.get_process_gids(self.pid)
        return nt_gids(real, effective, saved)

    @wrap_exceptions
    def get_process_terminal(self):
        tty_nr = _psutil_osx.get_process_tty_nr(self.pid)
        try:
            return _TERMINAL_MAP[tty_nr]
        except KeyError:
            return None

    @wrap_exceptions
    def get_memory_info(self):
        """Return a tuple with the process' RSS and VMS size."""
        rss, vms = _psutil_osx.get_memory_info(self.pid)
        return nt_meminfo(rss, vms)

    @wrap_exceptions
    def get_cpu_times(self):
        user, system = _psutil_osx.get_cpu_times(self.pid)
        return nt_cputimes(user, system)

    @wrap_exceptions
    def get_process_create_time(self):
        """Return the start time of the process as a number of seconds since
        the epoch."""
        return _psutil_osx.get_process_create_time(self.pid)

    @wrap_exceptions
    def get_process_num_threads(self):
        """Return the number of threads belonging to the process."""
        return _psutil_osx.get_process_num_threads(self.pid)

    @wrap_exceptions
    def get_open_files(self):
        """Return files opened by process."""
        if self.pid == 0:
            return []
        files = []
        rawlist = _psutil_osx.get_process_open_files(self.pid)
        for path, fd in rawlist:
            if os.path.isfile(path):
                ntuple = nt_openfile(path, fd)
                files.append(ntuple)
        return files

    @wrap_exceptions
    def get_connections(self, kind='inet'):
        """Return etwork connections opened by a process as a list of
        namedtuples.
        """
        if kind not in conn_tmap:
            raise ValueError("invalid %r kind argument; choose between %s"
                             % (kind, ', '.join([repr(x) for x in conn_tmap])))
        families, types = conn_tmap[kind]
        ret = _psutil_osx.get_process_connections(self.pid, families, types)
        return [nt_connection(*conn) for conn in ret]

    @wrap_exceptions
    def get_num_fds(self):
        if self.pid == 0:
            return 0
        return _psutil_osx.get_process_num_fds(self.pid)

    @wrap_exceptions
    def process_wait(self, timeout=None):
        try:
            return _psposix.wait_pid(self.pid, timeout)
        except TimeoutExpired:
            raise TimeoutExpired(self.pid, self._process_name)

    @wrap_exceptions
    def get_process_nice(self):
        return _psutil_posix.getpriority(self.pid)

    @wrap_exceptions
    def set_process_nice(self, value):
        return _psutil_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def get_process_status(self):
        code = _psutil_osx.get_process_status(self.pid)
        if code in _status_map:
            return _status_map[code]
        return constant(-1, "?")

    @wrap_exceptions
    def get_process_threads(self):
        """Return the number of threads belonging to the process."""
        rawlist = _psutil_osx.get_process_threads(self.pid)
        retlist = []
        for thread_id, utime, stime in rawlist:
            ntuple = nt_thread(thread_id, utime, stime)
            retlist.append(ntuple)
        return retlist

    nt_mmap_grouped = namedtuple('mmap',
        'path rss private swapped dirtied ref_count shadow_depth')
    nt_mmap_ext = namedtuple('mmap',
        'addr perms path rss private swapped dirtied ref_count shadow_depth')

    @wrap_exceptions
    def get_memory_maps(self):
        return _psutil_osx.get_process_memory_maps(self.pid)
