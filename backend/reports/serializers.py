from rest_framework import serializers

from users.serializers import UserDirectorySerializer


class ReportFiltersSerializer(serializers.Serializer):
    """FR-082: validates the ?start=&end=&project= query params."""
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)
    project = serializers.IntegerField(required=False)

    def validate(self, attrs):
        if 'start' in attrs and 'end' in attrs and attrs['start'] > attrs['end']:
            raise serializers.ValidationError('The start date must be before the end date.')
        return attrs


class EmployeeWorkloadSerializer(serializers.Serializer):
    user = UserDirectorySerializer()
    total = serializers.IntegerField()
    completed = serializers.IntegerField()
    overdue = serializers.IntegerField()


class ProjectProgressSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    status = serializers.CharField()
    progress = serializers.IntegerField()
    task_count = serializers.IntegerField()


class OverdueTaskSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    title = serializers.CharField()
    project = serializers.CharField(allow_null=True)
    assignee = UserDirectorySerializer(allow_null=True)
    due_date = serializers.DateField()


class ReportSerializer(serializers.Serializer):
    """FR-078 to FR-084: the report summary payload."""
    start = serializers.DateField()
    end = serializers.DateField()
    tasks_created = serializers.IntegerField()
    tasks_completed = serializers.IntegerField()
    tasks_overdue = serializers.IntegerField()
    overdue_tasks = OverdueTaskSerializer(many=True)
    avg_completion_days = serializers.FloatField(allow_null=True)
    tasks_by_priority = serializers.DictField(child=serializers.IntegerField())
    tasks_by_status = serializers.DictField(child=serializers.IntegerField())
    tasks_by_employee = EmployeeWorkloadSerializer(many=True)
    projects = ProjectProgressSerializer(many=True)
