import asyncio
import httpx
import time
from datetime import datetime
import csv
import pandas as pd
import sys
import os
import argparse
from dotenv import load_dotenv
from collections import namedtuple
import numpy as np
from algorithms import SchedulerAlgorithms

# --- Konfigurasi (Tidak ada perubahan) ---
load_dotenv()
VM_SPECS = {
    'vm1': {'ip': os.getenv("VM1_IP"), 'cpu': 1}, 'vm2': {'ip': os.getenv("VM2_IP"), 'cpu': 2},
    'vm3': {'ip': os.getenv("VM3_IP"), 'cpu': 4}, 'vm4': {'ip': os.getenv("VM4_IP"), 'cpu': 8},
}
VM_PORT = 5000
RESULTS_FILE = "all_runs_results.csv"

VM = namedtuple('VM', ['name', 'ip', 'cpu_cores'])
Task = namedtuple('Task', ['id', 'name', 'index', 'cpu_load'])

# --- (Fungsi load_tasks dan execute_task_on_vm tidak berubah) ---
def load_tasks(dataset_path: str) -> list[Task]:
    if not os.path.exists(dataset_path):
        print(f"Error: File dataset '{dataset_path}' tidak ditemukan.", file=sys.stderr); sys.exit(1)
    tasks = [];
    with open(dataset_path, 'r') as f:
        for i, line in enumerate(f):
            try:
                index = int(line.strip());
                if not 1 <= index <= 10: continue
                cpu_load = (index ** 2) * 10000
                tasks.append(Task(id=i, name=f"task-{index}-{i}", index=index, cpu_load=cpu_load))
            except ValueError: continue
    print(f"Berhasil memuat {len(tasks)} tugas dari {dataset_path}"); return tasks

async def execute_task_on_vm(task: Task, vm: VM, client: httpx.AsyncClient, 
                            vm_semaphore: asyncio.Semaphore, results_list: list):
    url = f"http://{vm.ip}:{VM_PORT}/task/{task.index}"; task_start_time = None; task_finish_time = None
    task_exec_time = -1.0; task_wait_time = -1.0; wait_start_mono = time.monotonic()
    try:
        async with vm_semaphore:
            task_wait_time = time.monotonic() - wait_start_mono
            print(f"  > Mengeksekusi task-{task.index} di {vm.name}...")
            task_start_mono = time.monotonic(); task_start_time = datetime.now()
            response = await client.get(url, timeout=300.0); response.raise_for_status()
            task_finish_time = datetime.now(); task_exec_time = time.monotonic() - task_start_mono
    except Exception as e:
        print(f"  !! Error pada task-{task.index} di {vm.name}: {e}", file=sys.stderr)
    finally:
        if task_start_time is None: task_start_time = datetime.now()
        if task_finish_time is None: task_finish_time = datetime.now()
        results_list.append({"task_id": task.id, "vm_assigned": vm.name, "start_time": task_start_time, 
                             "exec_time": task_exec_time, "finish_time": task_finish_time, "wait_time": task_wait_time})

# --- (Fungsi append_results_to_csv tidak berubah) ---
def append_results_to_csv(results_list: list, run_id: int, algorithm: str, dataset: str):
    if not results_list: return
    file_exists = os.path.exists(RESULTS_FILE)
    headers = ["run_id", "algorithm", "dataset", "task_id", "vm_assigned", "start_time_rel", "exec_time", "finish_time_rel", "wait_time"]
    valid_start_times = [r['start_time'] for r in results_list if r['start_time']]
    if not valid_start_times: return
    min_start = min(valid_start_times)
    formatted_results = []
    for r in results_list:
        new_r = r.copy(); new_r['run_id'] = run_id; new_r['algorithm'] = algorithm; new_r['dataset'] = dataset
        if r['start_time']:
            new_r['start_time_rel'] = (r['start_time'] - min_start).total_seconds()
            new_r['finish_time_rel'] = (r['finish_time'] - min_start).total_seconds()
        del new_r['start_time'], new_r['finish_time']
        formatted_results.append(new_r)
    with open(RESULTS_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists: writer.writeheader()
        writer.writerows(formatted_results)

# --- FUNGSI BARU: Menghitung metrik untuk satu kali run ---
def calculate_run_metrics(results_list: list, vms: list[VM], total_schedule_time: float):
    df = pd.DataFrame(results_list); success_df = df[df['exec_time'] > 0].copy()
    if success_df.empty: return None
    
    num_tasks = len(success_df)
    makespan = total_schedule_time
    throughput = num_tasks / makespan if makespan > 0 else 0
    total_cpu_time = success_df['exec_time'].sum()
    total_wait_time = success_df['wait_time'].sum()
    avg_exec_time = success_df['exec_time'].mean()
    
    min_start = success_df['start_time'].min()
    success_df['rel_start_time'] = (success_df['start_time'] - min_start).dt.total_seconds()
    success_df['rel_finish_time'] = (success_df['finish_time'] - min_start).dt.total_seconds()
    avg_start_time = success_df['rel_start_time'].mean()
    avg_finish_time = success_df['rel_finish_time'].mean()
    
    vm_exec_times = success_df.groupby('vm_assigned')['exec_time'].sum()
    imbalance_degree = (vm_exec_times.max() - vm_exec_times.min()) / vm_exec_times.mean() if vm_exec_times.mean() > 0 else 0
    
    total_cores = sum(vm.cpu_cores for vm in vms)
    total_available_cpu_time = makespan * total_cores
    resource_utilization = total_cpu_time / total_available_cpu_time if total_available_cpu_time > 0 else 0

    return {
        "Total Tugas Selesai": num_tasks, "Makespan (Waktu Total)": makespan,
        "Throughput": throughput, "Total CPU Time": total_cpu_time,
        "Total Wait Time": total_wait_time, "Average Start Time (rel)": avg_start_time,
        "Average Execution Time": avg_exec_time, "Average Finish Time (rel)": avg_finish_time,
        "Imbalance Degree": imbalance_degree, "Resource Utilization (CPU)": resource_utilization * 100
    }

# --- FUNGSI BARU: Menampilkan rangkuman akhir ---
def print_final_summary(run_metrics_list: list):
    if not run_metrics_list: return

    df = pd.DataFrame(run_metrics_list)
    avg_metrics = df.mean()

    print("\n--- Hasil ---")
    print(f"Total Tugas Selesai       : {avg_metrics['Total Tugas Selesai']:.0f}")
    print(f"Makespan (Waktu Total)    : {avg_metrics['Makespan (Waktu Total)']:.4f} detik")
    print(f"Throughput                : {avg_metrics['Throughput']:.4f} tugas/detik")
    print(f"Total CPU Time            : {avg_metrics['Total CPU Time']:.4f} detik")
    print(f"Total Wait Time           : {avg_metrics['Total Wait Time']:.4f} detik")
    print(f"Average Start Time (rel)  : {avg_metrics['Average Start Time (rel)']:.4f} detik")
    print(f"Average Execution Time    : {avg_metrics['Average Execution Time']:.4f} detik")
    print(f"Average Finish Time (rel) : {avg_metrics['Average Finish Time (rel)']:.4f} detik")
    print(f"Imbalance Degree          : {avg_metrics['Imbalance Degree']:.4f}")
    print(f"Resource Utilization (CPU): {avg_metrics['Resource Utilization (CPU)']:.4f}%")

async def run_single_test(run_id: int, algorithm: str, dataset_path: str, vms: list, tasks: list):
    # ... (Fungsi ini tidak berubah)
    print(f"\n--- [UJI COBA #{run_id+1}/10] Algoritma: {algorithm.upper()}, Dataset: {dataset_path} ---")
    scheduler = SchedulerAlgorithms(vms); assignment = None
    if algorithm == 'rr': assignment = scheduler.schedule_round_robin(tasks)
    elif algorithm == 'fcfs': assignment = scheduler.schedule_fcfs(tasks)
    elif algorithm == 'shc': assignment = scheduler.schedule_stochastic_hill_climbing(tasks, iterations=500)
    elif algorithm == 'erwca': assignment = scheduler.schedule_erwca(tasks, k_best=2)
    if not assignment: return None, None
    results_list = []; tasks_dict = {t.id: t for t in tasks}; vms_dict = {v.name: v for v in vms}
    vm_semaphores = {vm.name: asyncio.Semaphore(vm.cpu_cores) for vm in vms}
    async with httpx.AsyncClient() as client:
        coroutines = [execute_task_on_vm(tasks_dict[tid], vms_dict[vname], client, vm_semaphores[vname], results_list)
                      for tid, vname in assignment.items()]
        start_time = time.monotonic()
        await asyncio.gather(*coroutines)
        total_time = time.monotonic() - start_time
    print(f"  -> Selesai dalam {total_time:.4f} detik (Makespan)")
    return results_list, total_time

def main(algorithm: str, dataset_type: str, clean_start: bool):
    if clean_start and os.path.exists(RESULTS_FILE):
        print(f"Menghapus file hasil lama: {RESULTS_FILE}"); os.remove(RESULTS_FILE)
        
    dataset_map = {'simple': 'dataset_random_simple.txt', 'stratified': 'dataset_random_stratified.txt', 'lowhigh': 'dataset_low_high.txt'}
    dataset_path = dataset_map.get(dataset_type)
    if not dataset_path:
        print(f"Error: Tipe dataset '{dataset_type}' tidak valid."); return

    vms = [VM(name, spec['ip'], spec['cpu']) for name, spec in VM_SPECS.items()]
    tasks = load_tasks(dataset_path)
    if not tasks: return

    run_metrics_list = []
    for i in range(10):
        results, makespan = asyncio.run(run_single_test(i, algorithm, dataset_path, vms, tasks))
        if results:
            append_results_to_csv(results, i+1, algorithm, dataset_type)
            metrics = calculate_run_metrics(results, vms, makespan)
            if metrics:
                run_metrics_list.append(metrics)
    
    if run_metrics_list:
        print_final_summary(run_metrics_list)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Task Scheduler Test Harness")
    parser.add_argument('algorithm', type=str, choices=['rr', 'fcfs', 'shc', 'erwca'], help="Pilih algoritma")
    parser.add_argument('dataset', type=str, choices=['simple', 'stratified', 'lowhigh'], help="Pilih tipe dataset")
    parser.add_argument('--clean', action='store_true', help="Hapus file hasil lama sebelum memulai.")
    args = parser.parse_args()
    
    main(args.algorithm, args.dataset, args.clean)