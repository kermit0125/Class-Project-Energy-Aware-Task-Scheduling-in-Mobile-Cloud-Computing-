import matplotlib.pyplot as plt
import networkx as nx
import os

# Step 1: Define the task graph and execution table
def create_task_graph():
    G = nx.DiGraph()
    G.add_edges_from([
        (1, 2), (1, 3), (1, 4), (1, 5), (1, 6),
        (2, 7), (2, 8), (3, 7), (4, 7), (4, 9),
        (5, 8), (6, 10), (7, 10), (8, 10), (9, 10)
    ])
    
    execution_times = {
        1: [9, 7, 5], 2: [8, 6, 5], 3: [6, 5, 4],
        4: [7, 5, 3], 5: [5, 4, 2], 6: [7, 6, 4],
        7: [8, 5, 3], 8: [6, 4, 2], 9: [5, 3, 2], 10: [7, 4, 2]
    }
    return G, execution_times

# Step 2: Compute task priorities based on critical path
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

    # Return tasks sorted by priority in descending order
    return sorted(priorities.keys(), key=lambda x: priorities[x], reverse=True)

# Step 3: Initial Scheduling Algorithm
def initial_scheduling(G, execution_times, T_send, T_cloud, T_receive):
    scheduled_tasks = {}
    cores = [0, 0, 0]
    wireless_sending = 0
    wireless_receiving = 0

    # Compute task priorities
    task_order = compute_priorities(G, execution_times)

    for task in task_order:
        preds = list(G.predecessors(task))
        ready_time = 0
        for pred in preds:
            if scheduled_tasks[pred]['location'] == 'core':
                ready_time = max(ready_time, scheduled_tasks[pred]['finish_time'])
            elif scheduled_tasks[pred]['location'] == 'cloud':
                ready_time = max(ready_time, scheduled_tasks[pred]['finish_time_cloud'])

        core_times = [max(cores[i], ready_time) + execution_times[task][i] for i in range(3)]
        best_core = core_times.index(min(core_times))
        local_finish_time = core_times[best_core]

        start_sending = max(wireless_sending, ready_time)
        start_cloud = start_sending + T_send
        finish_cloud = start_cloud + T_cloud
        start_receiving = finish_cloud
        cloud_finish_time = start_receiving + T_receive

        if cloud_finish_time < local_finish_time:
            scheduled_tasks[task] = {
                'start_time': start_sending,
                'finish_time': cloud_finish_time,
                'location': 'cloud',
                'start_time_cloud': start_cloud,
                'finish_time_cloud': finish_cloud
            }
            wireless_sending = start_sending + T_send
            wireless_receiving = cloud_finish_time
        else:
            scheduled_tasks[task] = {
                'finish_time': local_finish_time,
                'location': 'core',
                'core': best_core + 1
            }
            cores[best_core] = local_finish_time

    return scheduled_tasks

# Step 4: Visualize Initial Scheduling
def visualize_scheduling(scheduled_tasks, execution_times, filename):
    colors = plt.cm.tab10(range(len(scheduled_tasks)))
    task_colors = {task: colors[i] for i, task in enumerate(scheduled_tasks)}

    plt.figure(figsize=(12, 6))
    for task, details in scheduled_tasks.items():
        color = task_colors[task]
        if details['location'] == 'core':
            core = details['core']
            execution_time = execution_times[task][core - 1]
            start_time = details['finish_time'] - execution_time
            plt.barh(f'Core {core}', execution_time, left=start_time,
                     color=color, edgecolor='black', label=f'Task {task}')
            # Add task number on the bar
            plt.text(start_time + execution_time / 2, f'Core {core}',
                     str(task), va='center', ha='center', color='white', fontsize=8)
        elif details['location'] == 'cloud':
            start_time = details['start_time']
            plt.barh('Wireless Sending', T_send, left=start_time, color=color, edgecolor='black', label=f'Task {task}')
            plt.text(start_time + T_send / 2, 'Wireless Sending',
                     str(task), va='center', ha='center', color='white', fontsize=8)
            plt.barh('Cloud', T_cloud, left=details['start_time_cloud'], color=color, edgecolor='black')
            plt.text(details['start_time_cloud'] + T_cloud / 2, 'Cloud',
                     str(task), va='center', ha='center', color='white', fontsize=8)
            plt.barh('Wireless Receiving', T_receive, left=details['start_time_cloud'] + T_cloud, color=color, edgecolor='black')
            plt.text(details['start_time_cloud'] + T_cloud + T_receive / 2, 'Wireless Receiving',
                     str(task), va='center', ha='center', color='white', fontsize=8)

    plt.xlabel("Time")
    plt.ylabel("Execution Units")
    plt.title("Task Scheduling Result")
    plt.xticks(ticks=range(0, int(plt.xlim()[1]) + 1, 2))  # Set x-axis ticks to increments of 2
    plt.grid(axis='x')

    handles, labels = plt.gca().get_legend_handles_labels()
    unique_labels = {}
    for handle, label in zip(handles, labels):
        if label not in unique_labels:
            unique_labels[label] = handle
    plt.legend(unique_labels.values(), unique_labels.keys(), loc='upper right', fontsize='small')

    plt.savefig(filename)
    plt.close()

# Step 5: Save Results to Folder
def save_results_with_table(scheduled_tasks, execution_times, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

    visualize_scheduling(scheduled_tasks, execution_times, os.path.join(folder, 'initial_scheduling.png'))

    # Save scheduling data to file
    scheduling_file = os.path.join(folder, 'scheduling.txt')
    with open(scheduling_file, 'w') as f:
        f.write("=== Task Scheduling Table ===\n")
        f.write(f"{'Task':<6} {'Start Time':<12} {'Finish Time':<12} {'Location':<10} {'Core':<6}\n")
        for task, details in scheduled_tasks.items():
            start_time = details['finish_time'] - execution_times[task][details.get('core', 1) - 1] if details['location'] == 'core' else details['start_time']
            location = details['location'].capitalize()
            core = details.get('core', '-')
            f.write(f"{task:<6} {start_time:<12} {details['finish_time']:<12} {location:<10} {core:<6}\n")

    # Display scheduling table in the terminal
    print("\n=== Task Scheduling Table ===")
    print(f"{'Task':<6} {'Start Time':<12} {'Finish Time':<12} {'Location':<10} {'Core':<6}")
    for task, details in scheduled_tasks.items():
        start_time = details['finish_time'] - execution_times[task][details.get('core', 1) - 1] if details['location'] == 'core' else details['start_time']
        location = details['location'].capitalize()
        core = details.get('core', '-')
        print(f"{task:<6} {start_time:<12} {details['finish_time']:<12} {location:<10} {core:<6}")

    print(f"\nScheduling table saved to: {scheduling_file}")

# Add energy computation function
def compute_energy(scheduled_tasks, execution_times, T_send, T_receive):
    core_powers = {1: 1, 2: 2, 3: 4}  # Power of Core1, Core2, Core3
    rf_power = 0.5  # Power for RF communication

    core_energy = {1: 0, 2: 0, 3: 0}
    cloud_energy = 0

    for task, details in scheduled_tasks.items():
        if details['location'] == 'core':
            core = details['core']
            execution_time = execution_times[task][core - 1]
            core_energy[core] += core_powers[core] * execution_time
        elif details['location'] == 'cloud':
            # Energy for sending and receiving
            cloud_energy += rf_power * T_send

    total_energy = sum(core_energy.values()) + cloud_energy
    return core_energy, cloud_energy, total_energy

# Update save_results_with_table to include energy computation
def save_results_with_table_and_energy(scheduled_tasks, execution_times, T_send, T_receive, folder):
    if not os.path.exists(folder):
        os.makedirs(folder)

    visualize_scheduling(scheduled_tasks, execution_times, os.path.join(folder, 'initial_scheduling.png'))

    # Save scheduling data to file
    scheduling_file = os.path.join(folder, 'scheduling.txt')
    with open(scheduling_file, 'w') as f:
        f.write("=== Task Scheduling Table ===\n")
        f.write(f"{'Task':<6} {'Start Time':<12} {'Finish Time':<12} {'Location':<10} {'Core':<6}\n")
        for task, details in scheduled_tasks.items():
            start_time = details['finish_time'] - execution_times[task][details.get('core', 1) - 1] if details['location'] == 'core' else details['start_time']
            location = details['location'].capitalize()
            core = details.get('core', '-')
            f.write(f"{task:<6} {start_time:<12} {details['finish_time']:<12} {location:<10} {core:<6}\n")

    # Display scheduling table in the terminal
    print("\n=== Task Scheduling Table ===")
    print(f"{'Task':<6} {'Start Time':<12} {'Finish Time':<12} {'Location':<10} {'Core':<6}")
    for task, details in scheduled_tasks.items():
        start_time = details['finish_time'] - execution_times[task][details.get('core', 1) - 1] if details['location'] == 'core' else details['start_time']
        location = details['location'].capitalize()
        core = details.get('core', '-')
        print(f"{task:<6} {start_time:<12} {details['finish_time']:<12} {location:<10} {core:<6}")

    # Compute and display energy consumption
    core_energy, cloud_energy, total_energy = compute_energy(scheduled_tasks, execution_times, T_send, T_receive)
    print("\n=== Energy Consumption ===")
    print(f"Core 1 Energy: {core_energy[1]}")
    print(f"Core 2 Energy: {core_energy[2]}")
    print(f"Core 3 Energy: {core_energy[3]}")
    print(f"Cloud Energy: {cloud_energy}")
    print(f"Total Energy: {total_energy}")

    # Save energy report to file
    with open(os.path.join(folder, 'energy_report.txt'), 'w') as f:
        f.write("=== Energy Consumption Report ===\n")
        f.write(f"Core 1 Energy: {core_energy[1]}\n")
        f.write(f"Core 2 Energy: {core_energy[2]}\n")
        f.write(f"Core 3 Energy: {core_energy[3]}\n")
        f.write(f"Cloud Energy: {cloud_energy}\n")
        f.write(f"Total Energy: {total_energy}\n")

    print(f"\nEnergy report saved to: {os.path.join(folder, 'energy_report.txt')}")

# Main Execution
try:
    G, execution_times = create_task_graph()
    T_send, T_cloud, T_receive = 3, 1, 1
    scheduled_tasks = initial_scheduling(G, execution_times, T_send, T_cloud, T_receive)

    save_results_with_table_and_energy(scheduled_tasks, execution_times, T_send, T_receive, 'example2')
    print("Results saved successfully in 'example2' folder.")
except Exception as e:
    print(f"An error occurred: {e}")

