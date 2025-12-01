import numpy as np
import random

class SchedulerAlgorithm:
    def __init__(self, vms_config):
        self.vms = vms_config
        self.num_vms = len(vms_config)

    def _get_task_load(self, task_index):
        return (task_index ** 2) * 10000

    def _estimate_execution_time(self, task_load, vm_cpu_cores):
        BASE_EXECUTION_TIME = 1.0
        SCALE_FACTOR = 10000
        return (task_load / SCALE_FACTOR) * (BASE_EXECUTION_TIME / vm_cpu_cores)

    def schedule_erwca(self, tasks, k_best=2):
        vm_loads = np.zeros(self.num_vms)
        vm_cores = np.array([vm.cpu_cores for vm in self.vms])
        assignment = {}
        sorted_tasks = sorted(tasks, key=lambda t: t.cpu_load, reverse=True)

        for task in sorted_tasks:
            task_load = self._get_task_load(task.index)
            estimated_times = self._estimate_execution_time(task_load, vm_cores)
            potential_finish_times = vm_loads + estimated_times
            
            sorted_vm_indices = np.argsort(potential_finish_times)
            
            num_choices = min(k_best, self.num_vms)
            top_k_indices = sorted_vm_indices[:num_choices]
            
            chosen_vm_index = random.choice(top_k_indices)

            assignment[task.id] = self.vms[chosen_vm_index].name
            vm_loads[chosen_vm_index] += estimated_times[chosen_vm_index]
            
        return assignment