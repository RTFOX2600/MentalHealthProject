from django.contrib import admin
from .models import (
    Student, CanteenConsumptionRecord, SchoolGateAccessRecord,
    DormitoryAccessRecord, NetworkAccessRecord, AcademicRecord
)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'name', 'college', 'major', 'grade']
    list_filter = ['college', 'major', 'grade']
    search_fields = ['student_id', 'name']
    ordering = ['student_id']


@admin.register(CanteenConsumptionRecord)
class CanteenConsumptionRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'month', 'amount']
    list_filter = ['month']
    search_fields = ['student__student_id', 'student__name']
    ordering = ['-month', 'student__student_id']


@admin.register(SchoolGateAccessRecord)
class SchoolGateAccessRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'timestamp', 'gate_location', 'direction']
    list_filter = ['gate_location', 'direction', 'timestamp']
    search_fields = ['student__student_id', 'student__name']
    ordering = ['-timestamp']


@admin.register(DormitoryAccessRecord)
class DormitoryAccessRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'timestamp', 'building', 'direction']
    list_filter = ['building', 'direction', 'timestamp']
    search_fields = ['student__student_id', 'student__name']
    ordering = ['-timestamp']


@admin.register(NetworkAccessRecord)
class NetworkAccessRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'start_time', 'end_time', 'use_vpn']
    list_filter = ['use_vpn', 'start_time']
    search_fields = ['student__student_id', 'student__name']
    ordering = ['-start_time']


@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ['student', 'month', 'average_score']
    list_filter = ['month']
    search_fields = ['student__student_id', 'student__name']
    ordering = ['-month', 'student__student_id']
