import asyncio
import httpx
import time
from datetime import datetime
import csv
import pandas as pd
import sys
import os
from dotenv import load_dotenv
from collections import namedtuple

from erwca_algorithm import SchedulerAlgorithm

load_dotenv()

VM_SPECS = {
    'vm1': {'ip': os.getenv("VM1_IP"), 'cpu_cores': 1, 'ram_gb': 1},
    'vm2': {'ip': os.getenv("VM2_IP"), 'cpu_cores': 2, 'ram_gb': 2},
    'vm3': {'ip': os.getenv("VM3_IP"), 'cpu_cores': 4, 'ram_gb': 4},
    'vm4': {'ip': os.getenv("VM4_IP"), 'cpu_cores': 8, 'ram_gb': 4},
}
VM_PORT = 5000
DATASET_FILE = 'dataset.txt'

VM = namedtuple('VM', ['name', 'ip', 'cpu_cores', 'ram_gb'])
Task = namedtuple('Task', ['id', 'name', 'index', 'cpu_load'])

# --- (Fungsi load_tasks dan execute_task_on_vm tetap sama) ---
def load_tasks(dataset_path: str) -> list[Task]:
    if not os.path.exists(dataset_path):
        print(f"Error: File dataset '{dataset_path}' tidak ditemukan.", file=sys.stderr)
        sys.exit(1)
    tasks = []
    with open(dataset_path, 'r') as f:
        for i, line in enumerate(f):
            try:
                index = int(line.strip())
                if not 1 <= index <= 10:
                    print(f"Peringatan: Task index {index} di baris {i+1} di luar rentang (1-10).")
                    continue
                cpu_load = (index ** 2) * 10000
                task_name = f"task-{index}-{i}"
                tasks.append(Task(id=i, name=task_name, index=index, cpu_load=cpu_load))
            except ValueError:
                print(f"Peringatan: Mengabaikan baris {i+1} yang tidak valid: '{line.strip()}'")
    print(f"Berhasil memuat {len(tasks)} tugas dari {dataset_path}")
    return tasks

async def execute_task_on_vm(task: Task, vm: VM, client: httpx.AsyncClient, 
                            vm_semaphore: asyncio.Semaphore, results_list: list):
    url = f"http://{vm.ip}:{VM_PORT}/task/{task.index}"; task_start_time = None; task_finish_time = None
    task_exec_time = -1.0; task_wait_time = -1.0; wait_start_mono = time.monotonic()
    try:
        async with vm_semaphore:
            task_wait_time = time.monotonic() - wait_start_mono
            print(f"Mengeksekusi {task.name} (idx: {task.id}) di {vm.name} (IP: {vm.ip})...")
            task_start_mono = time.monotonic(); task_start_time = datetime.now()
            response = await client.get(url, timeout=300.0)
            response.raise_for_status()
            task_finish_time = datetime.now(); task_exec_time = time.monotonic() - task_start_mono
            print(f"Selesai {task.name} (idx: {task.id}) di {vm.name}. Waktu: {task_exec_time:.4f}s")
    except Exception as e:
        print(f"Error pada {task.name} di {vm.name}: {e}", file=sys.stderr)
    finally:
        if task_start_time is None: task_start_time = datetime.now()
        if task_finish_time is None: task_finish_time = datetime.now()
        results_list.append({
            "index": task.id, "task_name": task.name, "vm_assigned": vm.name,
            "start_time": task_start_time, "exec_time": task_exec_time,
            "finish_time": task_finish_time, "wait_time": task_wait_time
        })

# --- FUNGSI write_results_to_csv (MODIFIKASI UTAMA) ---
def write_results_to_csv(results_list: list, run_id: str):
    if not results_list: return
    
    filename = "all_runs_erwca.csv"
    file_exists = os.path.exists(filename)
    
    headers = ["run_id", "index", "task_name", "vm_assigned", "start_time", "exec_time", "finish_time", "wait_time"]
    
    min_start_time = min(r['start_time'] for r in results_list)
    
    formatted_results = []
    for r in results_list:
        new_r = r.copy()
        new_r['run_id'] = run_id
        new_r['start_time'] = (r['start_time'] - min_start_time).total_seconds()
        new_r['finish_time'] = (r['finish_time'] - min_start_time).total_seconds()
        formatted_results.append(new_r)
    
    try:
        # Buka file dalam mode 'append' (a), bukan 'write' (w)
        with open(filename, 'a', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            # Hanya tulis header jika filenya baru dibuat
            if not file_exists:
                writer.writeheader()
            writer.writerows(formatted_results)
        print(f"\nData hasil eksekusi ditambahkan ke {filename}")
    except IOError as e:
        print(f"Error menulis ke CSV: {e}", file=sys.stderr)

# --- (Fungsi calculate_and_print_metrics tetap sama) ---
def calculate_and_print_metrics(results_list: list, vms: list[VM], total_schedule_time: float, run_id: str):
    df = pd.DataFrame(results_list); success_df = df[df['exec_time'] > 0].copy()
    if success_df.empty:
        print("Tidak ada tugas yang berhasil diselesaikan."); return
    
    num_tasks = len(success_df)
    total_cpu_time = success_df['exec_time'].sum()
    total_wait_time = success_df['wait_time'].sum()
    avg_exec_time = success_df['exec_time'].mean()
    
    min_start = success_df['start_time'].min()
    success_df['rel_start_time'] = (success_df['start_time'] - min_start).dt.total_seconds()
    success_df['rel_finish_time'] = (success_df['finish_time'] - min_start).dt.total_seconds()
    avg_start_time = success_df['rel_start_time'].mean()
    avg_finish_time = success_df['rel_finish_time'].mean()
    
    makespan = total_schedule_time
    throughput = num_tasks / makespan if makespan > 0 else 0
    
    vm_exec_times = success_df.groupby('vm_assigned')['exec_time'].sum()
    max_load = vm_exec_times.max(); min_load = vm_exec_times.min(); avg_load = vm_exec_times.mean()
    imbalance_degree = (max_load - min_load) / avg_load if avg_load > 0 else 0
    
    total_cores = sum(vm.cpu_cores for vm in vms)
    total_available_cpu_time = makespan * total_cores
    resource_utilization = total_cpu_time / total_available_cpu_time if total_available_cpu_time > 0 else 0

    print("\n--- Hasil ---")
    print(f"Total Tugas Selesai       : {num_tasks}")
    print(f"Makespan (Waktu Total)    : {makespan:.4f} detik")
    print(f"Throughput                : {throughput:.4f} tugas/detik")
    print(f"Total CPU Time            : {total_cpu_time:.4f} detik")
    print(f"Total Wait Time           : {total_wait_time:.4f} detik")
    print(f"Average Start Time (rel)  : {avg_start_time:.4f} detik")
    print(f"Average Execution Time    : {avg_exec_time:.4f} detik")
    print(f"Average Finish Time (rel) : {avg_finish_time:.4f} detik")
    print(f"Imbalance Degree          : {imbalance_degree:.4f}")
    print(f"Resource Utilization (CPU): {resource_utilization:.4%}")

async def main():
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    print(f"--- Memulai Uji Coba: {run_id} ---")

    vms = [VM(name, spec['ip'], spec['cpu_cores'], spec['ram_gb']) for name, spec in VM_SPECS.items()]
    tasks = load_tasks(DATASET_FILE)
    if not tasks: return

    scheduler = SchedulerAlgorithm(vms)
    best_assignment = scheduler.schedule_erwca(tasks, k_best=2)

    tasks_dict = {task.id: task for task in tasks}
    vms_dict = {vm.name: vm for vm in vms}

    results_list = []
    vm_semaphores = {vm.name: asyncio.Semaphore(vm.cpu_cores) for vm in vms}
    async with httpx.AsyncClient() as client:
        coroutines = [execute_task_on_vm(tasks_dict[task_id], vms_dict[vm_name], client, vm_semaphores[vm_name], results_list)
                      for task_id, vm_name in best_assignment.items()]
        
        print(f"\nMemulai eksekusi {len(coroutines)} tugas secara paralel...")
        schedule_start_time = time.monotonic()
        await asyncio.gather(*coroutines)
        total_schedule_time = time.monotonic() - schedule_start_time
        
        print(f"\nSemua eksekusi tugas selesai dalam {total_schedule_time:.4f} detik.")
    
    write_results_to_csv(results_list, run_id)
    calculate_and_print_metrics(results_list, vms, total_schedule_time, run_id)

if __name__ == "__main__":
    asyncio.run(main())