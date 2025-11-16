import numpy as np

class SchedulerAlgorithm:
    def __init__(self, vms_config):
        self.vms = vms_config
        self.num_vms = len(vms_config)
        self.rr_counter = 0

    def _get_task_load(self, task_index):
        return (task_index ** 2) * 10000

    def _estimate_execution_time(self, task_load, vm_cpu_cores):
        BASE_EXECUTION_TIME = 1.0
        SCALE_FACTOR = 10000
        return (task_load / SCALE_FACTOR) * (BASE_EXECUTION_TIME / vm_cpu_cores)

    def schedule_round_robin(self, tasks):
        assignment = {}
        for task in tasks:
            # DIUBAH: Menggunakan .name bukan ['name']
            vm_name = self.vms[self.rr_counter].name 
            assignment[task.id] = vm_name
            self.rr_counter = (self.rr_counter + 1) % self.num_vms
        return assignment

    def schedule_erwca(self, tasks):
        vm_loads = np.zeros(self.num_vms)
        # DIUBAH: Menggunakan .cpu_cores bukan ['cpu']
        vm_cores = np.array([vm.cpu_cores for vm in self.vms]) 
        assignment = {}
        sorted_tasks = sorted(tasks, key=lambda t: t.cpu_load, reverse=True)

        for task in sorted_tasks:
            task_load = self._get_task_load(task.index)
            estimated_times = self._estimate_execution_time(task_load, vm_cores)
            potential_finish_times = vm_loads + estimated_times
            best_vm_index = np.argmin(potential_finish_times)
            
            # DIUBAH: Menggunakan .name bukan ['name']
            assignment[task.id] = self.vms[best_vm_index].name
            vm_loads[best_vm_index] += estimated_times[best_vm_index]
            
        return assignment