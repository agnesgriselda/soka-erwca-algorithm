import numpy as np

class SchedulerAlgorithm:
    def __init__(self, vms_config):
        self.vms = vms_config
        self.num_vms = len(vms_config)

    def _get_task_load(self, task_index):
        # Rumus ini harus sama dengan yang ada di server.py
        return (task_index ** 2) * 10000

    def _estimate_execution_time(self, task_load, vm_cpu_cores):
        # Model sederhana untuk estimasi: waktu berbanding terbalik dengan jumlah core.
        BASE_EXECUTION_TIME = 1.0
        SCALE_FACTOR = 10000
        return (task_load / SCALE_FACTOR) * (BASE_EXECUTION_TIME / vm_cpu_cores)

    def schedule_erwca(self, tasks):
        """
        Menjadwalkan seluruh batch tugas menggunakan heuristik ErWCA.
        Strategi: Urutkan tugas dari yang terbesar, lalu berikan setiap tugas
        ke VM yang akan selesai paling cepat (minimalkan makespan secara greedy).
        """
        vm_loads = np.zeros(self.num_vms)
        vm_cores = np.array([vm.cpu_cores for vm in self.vms])
        assignment = {}

        # Urutkan tugas dari yang terbesar ke terkecil
        sorted_tasks = sorted(tasks, key=lambda t: t.cpu_load, reverse=True)

        for task in sorted_tasks:
            task_load = self._get_task_load(task.index)
            
            # Estimasi waktu eksekusi tugas ini di setiap VM
            estimated_times = self._estimate_execution_time(task_load, vm_cores)
            
            # Cari VM yang akan selesai paling cepat jika diberi tugas ini
            potential_finish_times = vm_loads + estimated_times
            best_vm_index = np.argmin(potential_finish_times)
            
            # Tugaskan dan perbarui beban estimasi VM
            assignment[task.id] = self.vms[best_vm_index].name
            vm_loads[best_vm_index] += estimated_times[best_vm_index]
            
        return assignment