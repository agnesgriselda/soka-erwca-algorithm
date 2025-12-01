import numpy as np
import random

class SchedulerAlgorithms:
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

    def _calculate_makespan_for_shc(self, assignment, tasks_dict):
        vm_loads = np.zeros(self.num_vms)
        vm_map = {vm.name: i for i, vm in enumerate(self.vms)}
        vm_cores = np.array([vm.cpu_cores for vm in self.vms])
        for task_id, vm_name in assignment.items():
            task = tasks_dict[task_id]
            task_load = self._get_task_load(task.index)
            vm_index = vm_map[vm_name]
            exec_time = self._estimate_execution_time(task_load, vm_cores[vm_index])
            vm_loads[vm_index] += exec_time
        return np.max(vm_loads)

    def schedule_round_robin(self, tasks):
        assignment = {}
        for task in tasks:
            vm_name = self.vms[self.rr_counter].name
            assignment[task.id] = vm_name
            self.rr_counter = (self.rr_counter + 1) % self.num_vms
        return assignment

    def schedule_fcfs(self, tasks):
        vm_loads = np.zeros(self.num_vms)
        vm_cores = np.array([vm.cpu_cores for vm in self.vms])
        assignment = {}
        for task in tasks:
            task_load = self._get_task_load(task.index)
            estimated_times = self._estimate_execution_time(task_load, vm_cores)
            potential_finish_times = vm_loads + estimated_times
            best_vm_index = np.argmin(potential_finish_times)
            assignment[task.id] = self.vms[best_vm_index].name
            vm_loads[best_vm_index] += estimated_times[best_vm_index]
        return assignment

    def schedule_stochastic_hill_climbing(self, tasks, iterations=500):
        tasks_dict = {task.id: task for task in tasks}
        current_solution = {task.id: random.choice(self.vms).name for task in tasks}
        current_makespan = self._calculate_makespan_for_shc(current_solution, tasks_dict)
        for _ in range(iterations):
            neighbor_solution = current_solution.copy()
            task_to_move = random.choice(tasks)
            new_vm = random.choice(self.vms)
            neighbor_solution[task_to_move.id] = new_vm.name
            neighbor_makespan = self._calculate_makespan_for_shc(neighbor_solution, tasks_dict)
            if neighbor_makespan < current_makespan:
                current_solution = neighbor_solution
                current_makespan = neighbor_makespan
        return current_solution

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