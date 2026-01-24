from django.contrib import admin
from .models import (
    UploadedDataSet, CanteenConsumption, SchoolGateRecord,
    DormGateRecord, NetworkAccessRecord, GradeRecord, AnalysisResult
)


@admin.register(UploadedDataSet)
class UploadedDataSetAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'uploaded_by', 'uploaded_at']
    list_filter = ['uploaded_at']
    search_fields = ['session_id', 'uploaded_by__username']


@admin.register(CanteenConsumption)
class CanteenConsumptionAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'month', 'consumption', 'dataset']
    list_filter = ['month']
    search_fields = ['student_id']


@admin.register(SchoolGateRecord)
class SchoolGateRecordAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'entry_time', 'direction', 'location']
    list_filter = ['direction', 'entry_time']
    search_fields = ['student_id']


@admin.register(DormGateRecord)
class DormGateRecordAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'entry_time', 'direction', 'building']
    list_filter = ['direction', 'entry_time']
    search_fields = ['student_id']


@admin.register(NetworkAccessRecord)
class NetworkAccessRecordAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'start_time', 'domain', 'use_vpn']
    list_filter = ['use_vpn', 'start_time']
    search_fields = ['student_id', 'domain']


@admin.register(GradeRecord)
class GradeRecordAdmin(admin.ModelAdmin):
    list_display = ['student_id', 'month', 'dataset']
    list_filter = ['month']
    search_fields = ['student_id']


@admin.register(AnalysisResult)
class AnalysisResultAdmin(admin.ModelAdmin):
    list_display = ['analysis_type', 'dataset', 'created_at']
    list_filter = ['analysis_type', 'created_at']
    search_fields = ['dataset__session_id']
