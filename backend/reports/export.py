"""FR-083: flatten a report into a downloadable CSV."""
import csv
import io


def report_to_csv(report):
    buf = io.StringIO()
    writer = csv.writer(buf)

    writer.writerow(['Report period', report['start'], 'to', report['end']])
    writer.writerow([])

    writer.writerow(['Summary'])
    writer.writerow(['Metric', 'Value'])
    writer.writerow(['Tasks created', report['tasks_created']])
    writer.writerow(['Tasks completed', report['tasks_completed']])
    writer.writerow(['Tasks overdue (current)', report['tasks_overdue']])
    writer.writerow(['Average completion time (days)', report['avg_completion_days'] if report['avg_completion_days'] is not None else ''])
    writer.writerow([])

    writer.writerow(['Tasks by priority (created in period)'])
    writer.writerow(['Priority', 'Count'])
    for priority, count in report['tasks_by_priority'].items():
        writer.writerow([priority, count])
    writer.writerow([])

    writer.writerow(['Tasks by status (current)'])
    writer.writerow(['Status', 'Count'])
    for status, count in report['tasks_by_status'].items():
        writer.writerow([status, count])
    writer.writerow([])

    writer.writerow(['Tasks by employee (current workload)'])
    writer.writerow(['Employee', 'Total', 'Completed', 'Overdue'])
    for row in report['tasks_by_employee']:
        name = row['user']['first_name'] + ' ' + row['user']['last_name']
        writer.writerow([name.strip() or row['user']['username'], row['total'], row['completed'], row['overdue']])
    writer.writerow([])

    writer.writerow(['Projects (current progress)'])
    writer.writerow(['Project', 'Status', 'Progress %', 'Task count'])
    for p in report['projects']:
        writer.writerow([p['name'], p['status'], p['progress'], p['task_count']])
    writer.writerow([])

    writer.writerow(['Overdue tasks (current)'])
    writer.writerow(['ID', 'Title', 'Project', 'Assignee', 'Due date'])
    for t in report['overdue_tasks']:
        assignee = t['assignee']
        assignee_name = (assignee['first_name'] + ' ' + assignee['last_name']).strip() or assignee['username'] if assignee else ''
        writer.writerow([t['id'], t['title'], t['project'] or '', assignee_name, t['due_date']])

    return buf.getvalue()
