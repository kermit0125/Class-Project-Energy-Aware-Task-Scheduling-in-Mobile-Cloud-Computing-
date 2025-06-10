import matplotlib.pyplot as plt
import networkx as nx
import os

def create_task_graph():
    G = nx.DiGraph()
    G.add_edges_from([
        (1, 2), (1, 3), (1, 4), (1, 5), (1, 6),
        (2, 8), (2, 9), (3, 7), (4, 8), (4, 9),
        (5, 9), (6, 8), (7, 10), (8, 10), (9, 10),
        (14, 1), (13, 1), (14, 15), (15, 12), (15, 8),
        (6, 12), (3, 11), (12, 20), (12, 16), (11, 17),
        (7, 18), (12, 16), (20, 16), (9, 19)
    ])
    
    execution_times = {
        1: [9, 7, 5], 2: [8, 6, 5], 3: [6, 5, 4],
        4: [7, 5, 3], 5: [5, 4, 2], 6: [7, 6, 4],
        7: [8, 5, 3], 8: [6, 4, 2], 9: [5, 3, 2], 
        10: [7, 4, 2], 11: [8, 3, 2], 12: [5, 3, 2],
        13: [6, 5, 4], 14: [4, 4, 3], 15: [6, 6, 5],
        16: [6, 6, 5], 17: [4, 3, 2], 18: [4, 3, 2],
        19: [5, 4, 2], 20: [8, 4, 2]
    }
    return G, execution_times

def compute_priorities(G, execution_times):
    priorities = {}
    successors = {node: list(G.successors(node)) for node in G.nodes()}

    def calculate_priority(task):
        if task in priorities:
            return priorities[task]
        succ_priorities = [calculate_priority(succ) for succ in successors[task]]
        priorities[task] = max(execution_times[task]) + (max(succ_priorities) if succ_priorities else 0)
        return priorities[task]

    for task in G.nodes():
        calculate_priority(task)

    return sorted(priorities.keys(), key=lambda x: priorities[x], reverse=True)

def initial_scheduling(G, execution_times, T_send, T_cloud, T_receive):
    scheduled_tasks = {}
    cores = [0, 0, 0]  # 每个核心的最早空闲时间
    core_task_queues = {i: [] for i in range(3)}  # 每个核心的任务队列
    wireless_sending = 0  # 无线发送最早空闲时间

    task_order = compute_priorities(G, execution_times)

    for task in task_order:
        preds = list(G.predecessors(task))
        
        # 计算 ready_time
        ready_time = 0
        for pred in preds:
            if scheduled_tasks[pred]['location'] == 'core':
                ready_time = max(ready_time, scheduled_tasks[pred]['finish_time'])
            elif scheduled_tasks[pred]['location'] == 'cloud':
                ready_time = max(ready_time, scheduled_tasks[pred]['start_time_cloud'])

        # 核心执行时间
        core_times = []
        core_ready_times = []  # 保存每个核心的准备时间
        for i in range(3):
            core_ready_time = cores[i]
            if core_task_queues[i]:  # 如果核心有任务，则需要考虑串行性
                core_ready_time = max(core_ready_time, core_task_queues[i][-1]['finish_time'])
            core_ready_times.append(core_ready_time)
            core_times.append(max(core_ready_time, ready_time) + execution_times[task][i])

        best_core = core_times.index(min(core_times))
        local_ready_time = max(cores[best_core], ready_time)
        local_start_time = max(core_ready_times[best_core], ready_time)
        local_finish_time = local_start_time + execution_times[task][best_core]

        # 云端执行时间
        start_sending = max(wireless_sending, ready_time)
        start_cloud = start_sending + T_send #最左边右顶点
        finish_cloud = start_cloud + T_cloud #中间右顶点
        start_receiving = finish_cloud       #中间右顶点
        cloud_finish_time = start_receiving + T_receive #右边右顶点

        # 选择更优的执行位置
        if cloud_finish_time < local_finish_time:
            scheduled_tasks[task] = {
                'ready_time': ready_time,
                'start_time': start_sending,
                'finish_time': cloud_finish_time,
                'location': 'cloud',
                'start_time_cloud': start_cloud,
                'finish_time_cloud': finish_cloud
            }
            wireless_sending = start_sending + T_send
        else:
            scheduled_tasks[task] = {
                'ready_time': ready_time,
                'start_time': local_start_time,
                'finish_time': local_finish_time,
                'location': 'core',
                'core': best_core + 1
            }
            cores[best_core] = local_finish_time
            core_task_queues[best_core].append(scheduled_tasks[task])  # 更新核心队列

    return scheduled_tasks

def kernel_algorithm(G, scheduled_tasks, execution_times, task, target, T_send, T_cloud, T_receive):
    new_scheduled_tasks = scheduled_tasks.copy()
    preds = list(G.predecessors(task))
    ready_time = 0
    for pred in preds:
        if scheduled_tasks[pred]['location'] == 'core':
            ready_time = max(ready_time, scheduled_tasks[pred]['finish_time'])
        elif scheduled_tasks[pred]['location'] == 'cloud':
            ready_time = max(ready_time, scheduled_tasks[pred]['start_time_cloud'])

    if target == 'core':
        cores = [0, 0, 0]
        core_times = [
            max(cores[i], ready_time) + execution_times[task][i]
            for i in range(3)
        ]
        best_core = core_times.index(min(core_times))
        local_finish_time = core_times[best_core]
        new_scheduled_tasks[task] = {
            'finish_time': local_finish_time,
            'location': 'core',
            'core': best_core + 1
        }
        cores[best_core] = local_finish_time
    elif target == 'cloud':
        start_sending = max(ready_time, 0)
        start_cloud = start_sending + T_send
        finish_cloud = start_cloud + T_cloud
        start_receiving = finish_cloud
        cloud_finish_time = start_receiving + T_receive
        new_scheduled_tasks[task] = {
            'start_time': start_sending,
            'finish_time': cloud_finish_time,
            'location': 'cloud',
            'start_time_cloud': start_cloud,
            'finish_time_cloud': finish_cloud
        }

    return new_scheduled_tasks

def compute_critical_path(G, scheduled_tasks, execution_times):
    critical_path = []
    max_time = 0
    for node in nx.topological_sort(G):
        preds = list(G.predecessors(node))

        if preds:
            start_time = max(scheduled_tasks[pred]['finish_time'] for pred in preds)
        else:
            start_time = 0

        if scheduled_tasks[node]['location'] == 'core':
            core = scheduled_tasks[node]['core'] - 1
            execution_time = execution_times[node][core]
        elif scheduled_tasks[node]['location'] == 'cloud':
            execution_time = 3 + 1 + 1

        finish_time = start_time + execution_time
        scheduled_tasks[node]['start_time'] = start_time
        scheduled_tasks[node]['finish_time'] = finish_time

        if finish_time > max_time:
            max_time = finish_time
            critical_path = [node]
        elif finish_time == max_time:
            critical_path.append(node)

    return critical_path, max_time

def compute_energy(scheduled_tasks, execution_times, T_send, T_receive):
    core_powers = {1: 1, 2: 2, 3: 4}
    rf_power = 0.5

    core_energy = {1: 0, 2: 0, 3: 0}
    cloud_energy = 0

    for task, details in scheduled_tasks.items():
        if details['location'] == 'core':
            core = details['core']
            execution_time = execution_times[task][core - 1]
            core_energy[core] += core_powers[core] * execution_time
        elif details['location'] == 'cloud':
            cloud_energy += rf_power * T_send
            cloud_energy += rf_power * T_receive

    total_energy = sum(core_energy.values()) + cloud_energy
    return core_energy, cloud_energy, total_energy

def recalculate_schedule_times(G, scheduled_tasks, execution_times, T_send, T_cloud, T_receive):
    cores = [0, 0, 0]  # 每个核心的最早空闲时间
    core_task_queues = {i: [] for i in range(3)}  # 每个核心的任务队列
    wireless_sending = 0  # 云端无线发送的最早空闲时间

    for node in nx.topological_sort(G):
        preds = list(G.predecessors(node))

        # 计算 ready_time
        if preds:
            ready_time = max(
                scheduled_tasks[pred]['finish_time'] if scheduled_tasks[pred]['location'] == 'core'
                else scheduled_tasks[pred]['start_time_cloud']
                for pred in preds
            )
        else:
            ready_time = 0

        # 根据任务位置计算 start_time 和 finish_time
        if scheduled_tasks[node]['location'] == 'core':
            core = scheduled_tasks[node]['core'] - 1
            core_ready_time = cores[core]
            if core_task_queues[core]:
                core_ready_time = core_task_queues[core][-1]['finish_time']
            start_time = max(ready_time, core_ready_time)
            execution_time = execution_times[node][core]
            finish_time = start_time + execution_time

            # 更新核心的空闲时间和任务队列
            cores[core] = finish_time
            core_task_queues[core].append({
                'task': node,
                'start_time': start_time,
                'finish_time': finish_time
            })

        elif scheduled_tasks[node]['location'] == 'cloud':
            start_sending = max(wireless_sending, ready_time)
            start_cloud = start_sending + T_send
            finish_cloud = start_cloud + T_cloud
            start_receiving = finish_cloud
            finish_time = start_receiving + T_receive

            start_time = start_sending  # 云端任务的起始时间是开始发送的时间
            execution_time = T_send + T_cloud + T_receive
            wireless_sending = start_sending + T_send  # 更新无线发送的空闲时间

        # 更新任务的时间信息
        scheduled_tasks[node]['ready_time'] = ready_time
        scheduled_tasks[node]['start_time'] = start_time
        scheduled_tasks[node]['finish_time'] = finish_time

def compute_critical_path(G, scheduled_tasks, execution_times, T_send, T_cloud, T_receive, T_max=27):
    """
    Compute the critical path based on serialized core execution and adjusted cloud dependencies.
    """
    critical_path = []
    max_time = 0
    print("\n=== Debug: Critical Path Computation ===")

    cores = [0, 0, 0]  # Keep track of core availability
    core_task_queues = {i: [] for i in range(3)}  # Core task queues for serialized execution
    wireless_sending = 0  # Cloud sending time tracking

    for node in nx.topological_sort(G):
        preds = list(G.predecessors(node))

        # Determine the ready time based on predecessors
        if preds:
            ready_time = max(
                scheduled_tasks[pred]['finish_time'] if scheduled_tasks[pred]['location'] == 'core'
                else scheduled_tasks[pred]['start_time_cloud']
                for pred in preds
            )
        else:
            ready_time = 0

        # Compute task start and finish time based on location
        if scheduled_tasks[node]['location'] == 'core':
            core = scheduled_tasks[node]['core'] - 1
            core_ready_time = cores[core]
            if core_task_queues[core]:
                core_ready_time = core_task_queues[core][-1]['finish_time']
            start_time = max(ready_time, core_ready_time)
            execution_time = execution_times[node][core]
            finish_time = start_time + execution_time
            location = f"Core {core + 1}"

            # Update core availability and task queue
            cores[core] = finish_time
            core_task_queues[core].append({
                'task': node,
                'start_time': start_time,
                'finish_time': finish_time
            })
        elif scheduled_tasks[node]['location'] == 'cloud':
            start_sending = max(wireless_sending, ready_time)
            start_cloud = start_sending + T_send
            finish_cloud = start_cloud + T_cloud
            start_receiving = finish_cloud
            finish_time = start_receiving + T_receive
            start_time = start_sending  # Start time for cloud tasks corresponds to the sending start time
            execution_time = T_send + T_cloud + T_receive
            location = "Cloud"

            # Update cloud availability
            wireless_sending = start_sending + T_send

        # Update scheduled task's timing
        scheduled_tasks[node]['ready_time'] = ready_time
        scheduled_tasks[node]['start_time'] = start_time
        scheduled_tasks[node]['finish_time'] = finish_time

        # Debug output for the current task
        print(f"Task {node}: Ready={ready_time}, Start={start_time}, Exec={execution_time}, Finish={finish_time}, Location={location}")

        # Update critical path and max_time
        if finish_time > max_time:
            max_time = finish_time
            critical_path = [node]
        elif finish_time == max_time:
            critical_path.append(node)
    
    core_energy, cloud_energy, total_energy = compute_energy(scheduled_tasks, execution_times, T_send, T_receive)
    print(f"Critical Path: {critical_path}, Max Time: {max_time}, Total Energy:{total_energy}\n")
    return critical_path, max_time

def task_migration_optimized(G, scheduled_tasks, execution_times, T_send, T_cloud, T_receive, T_max=39):
    final_schedule = scheduled_tasks.copy()

    for task in scheduled_tasks.keys():
        potential_schedules = []

        # 尝试迁移到每个核心
        for core in range(3):
            potential_schedule = kernel_algorithm(
                G, final_schedule, execution_times, task, 'core', T_send, T_cloud, T_receive
            )
            recalculate_schedule_times(G, potential_schedule, execution_times, T_send, T_cloud, T_receive)
            
            # 判断是否满足时间约束
            critical_path, critical_time = compute_critical_path(
                G, potential_schedule, execution_times, T_send, T_cloud, T_receive, T_max
            )
            if critical_time > T_max:
                continue  # 跳过不满足时间约束的迁移

            potential_schedules.append((potential_schedule, f'Core {core + 1}'))

        # 尝试迁移到云端
        potential_schedule = kernel_algorithm(
            G, final_schedule, execution_times, task, 'cloud', T_send, T_cloud, T_receive
        )
        recalculate_schedule_times(G, potential_schedule, execution_times, T_send, T_cloud, T_receive)
        
        # 判断是否满足时间约束
        critical_path, critical_time = compute_critical_path(
            G, potential_schedule, execution_times, T_send, T_cloud, T_receive, T_max
        )
        if critical_time <= T_max:
            potential_schedules.append((potential_schedule, 'Cloud'))

        # 比较所有可能的调度方案，选择最优的
        best_schedule = final_schedule
        best_energy = compute_energy(final_schedule, execution_times, T_send, T_receive)[2]
        best_time = max(t['finish_time'] for t in final_schedule.values())
        for schedule, target in potential_schedules:
            _, critical_time = compute_critical_path(
                G, schedule, execution_times, T_send, T_cloud, T_receive, T_max
            )
            _, _, energy = compute_energy(schedule, execution_times, T_send, T_receive)

            # 选择更优的迁移方案
            if critical_time <= T_max and (energy < best_energy or (energy == best_energy and critical_time < best_time)):
                best_schedule = schedule
                best_energy = energy
                best_time = critical_time

                print(f"Task {task} migrated to {target}: T_total = {critical_time}, Energy = {best_energy}, Critical Path = {critical_path}")

        final_schedule = best_schedule

    return final_schedule



def visualize_scheduling(scheduled_tasks, execution_times, T_send, T_cloud, T_receive, filename):
    colors = plt.cm.tab10(range(len(scheduled_tasks)))
    task_colors = {task: colors[i % 10] for i, task in enumerate(scheduled_tasks)}

    plt.figure(figsize=(20, 10))
    for task, details in scheduled_tasks.items():
        print(f"Task {task}: Start={details.get('start_time')}, Finish={details.get('finish_time')}, "
              f"Location={details.get('location')}, Core={details.get('core', '-')}")
        color = task_colors[task]
        if details['location'] == 'core':
            core = details['core']
            start_time = details['start_time']  # 使用直接的 ST
            finish_time = details['finish_time']  # 使用直接的 FT
            execution_time = finish_time - start_time  # 计算执行时间
            plt.barh(f'Core {core}', execution_time, left=start_time,
                     color=color, edgecolor='black', label=f'Task {task}')
            plt.text(start_time + execution_time / 2, f'Core {core}',
                     str(task), va='center', ha='center', color='white', fontsize=8)
        elif details['location'] == 'cloud':
            start_time = details.get('start_time')  # 云端任务的 ST
            cloud_start_time = start_time + 3  # 云端处理的 ST
            receive_start_time = cloud_start_time + 1

            # 绘制无线发送
            plt.barh('Wireless Sending', T_send, left=start_time, color=color, edgecolor='black', label=f'Task {task}')
            plt.text(start_time + T_send / 2, 'Wireless Sending',
                     str(task), va='center', ha='center', color='white', fontsize=8)

            # 绘制云端处理
            plt.barh('Cloud', T_cloud, left=cloud_start_time, color=color, edgecolor='black')
            plt.text(cloud_start_time + T_cloud / 2, 'Cloud',
                     str(task), va='center', ha='center', color='white', fontsize=8)

            # 绘制无线接收
            plt.barh('Wireless Receiving', T_receive, left=receive_start_time, color=color, edgecolor='black')
            plt.text(receive_start_time + T_receive / 2, 'Wireless Receiving',
                     str(task), va='center', ha='center', color='white', fontsize=8)

    plt.xlabel("Time")
    plt.ylabel("Execution Units")
    plt.title("Optimized Task Scheduling")
    plt.grid(axis='x')

    # 添加图例
    handles, labels = plt.gca().get_legend_handles_labels()
    unique_labels = {label: handle for handle, label in zip(handles, labels)}
    plt.legend(unique_labels.values(), unique_labels.keys(), loc='upper right', fontsize='small')

    plt.savefig(filename)
    plt.close()




def main():
    G, execution_times = create_task_graph()
    T_send, T_cloud, T_receive = 3, 1, 1

    # 初始调度
    initial_schedule = initial_scheduling(G, execution_times, T_send, T_cloud, T_receive)

    # 优化调度
    optimized_schedule = task_migration_optimized(G, initial_schedule, execution_times, T_send, T_cloud, T_receive)

    # 输出优化调度结果
    output_folder = 'Example5_Final'
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # 可视化优化调度
    visualize_scheduling(optimized_schedule, execution_times, T_send, T_cloud, T_receive,
                         os.path.join(output_folder, 'initial_scheduling.png'))

    # 保存调度表到 scheduling.txt
    with open(os.path.join(output_folder, 'scheduling.txt'), 'w') as f:
        f.write("=== Task Scheduling Table ===\n")
        f.write(f"{'Task':<6} {'Start Time':<12} {'Finish Time':<12} {'Location':<10} {'Core':<6}\n")
        for task, details in optimized_schedule.items():
            start_time = details.get('start_time', '-')
            finish_time = details['finish_time']
            location = details['location'].capitalize()
            core = details.get('core', '-')
            f.write(f"{task:<6} {start_time:<12} {finish_time:<12} {location:<10} {core:<6}\n")

    # 计算并保存能耗报告到 energy_report.txt
    core_energy, cloud_energy, total_energy = compute_energy(optimized_schedule, execution_times, T_send, T_receive)
    with open(os.path.join(output_folder, 'energy_report.txt'), 'w') as f:
        f.write("=== Energy Consumption Report ===\n")
        f.write(f"Core 1 Energy: {core_energy[1]}\n")
        f.write(f"Core 2 Energy: {core_energy[2]}\n")
        f.write(f"Core 3 Energy: {core_energy[3]}\n")
        f.write(f"Cloud Energy: {cloud_energy}\n")
        f.write(f"Total Energy: {total_energy}\n")

    print("Results saved to 'Example5_Final' folder")

if __name__ == '__main__':
    main()
