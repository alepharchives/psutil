import os
import signal


class Impl(object):
    def process_exists(self, pid):
        """Checks whether or not a process exists with the given PID."""
        return pid in self.get_pid_list()
        
    def get_process_info(self, pid):
        """Returns a process info class."""
        import psutil
        path = os.readlink("/proc/%s/exe" %pid)
        name = os.path.basename(path)
        f = open("/proc/%s/cmdline" %pid)
        try:
            cmdline = f.read().replace('\x00', ' ').strip()
        finally:
            f.close()
        return psutil.ProcessInfo(pid, name, path, cmdline)

    def kill_process(self, pid, sig=signal.SIGKILL):
        """Terminates the process with the given PID"""
        if sig is None:
            sig = signal.SIGKILL
        os.kill(pid, sig)
        
    def get_pid_list(self):
        """Returns a list of PIDs currently running on the system"""
        return [int(x) for x in os.listdir('/proc') if x.isdigit()]
