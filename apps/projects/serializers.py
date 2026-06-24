import re
from rest_framework import serializers
from .models import Project

class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = [
            'id', 'name', 'description', 'owner', 'created_at', 'updated_at',
            'business_context', 'goals', 'constraints', 'compliance', 'availability', 'repository_data'
        ]
        read_only_fields = ['owner', 'created_at', 'updated_at']

    def validate_business_context(self, value):
        if not isinstance(value, dict):
            return value
        expected_users = value.get('expectedUsers')
        if expected_users:
            expected_users = str(expected_users).strip()
            clean = re.sub(r'<[^>]*>?', '', expected_users)
            if clean != expected_users or not re.match(r'^[0-9,]+(\s*[kKmMbB]?(users|people)?)?$', clean.replace(' ', '')):
                raise serializers.ValidationError("Invalid Expected Users format. Script/HTML characters are not allowed.")
        return value

    def validate_constraints(self, value):
        if not isinstance(value, dict):
            return value
        budget = value.get('budget')
        if budget:
            budget = str(budget).strip()
            clean = re.sub(r'<[^>]*>?', '', budget)
            if clean != budget or not re.match(r'^[0-9a-zA-Z\s$,./\-\+kKmM]+$', clean):
                raise serializers.ValidationError("Invalid Budget Limits format. Script/HTML characters are not allowed.")
        return value

    def validate_availability(self, value):
        if not isinstance(value, dict):
            return value
        
        sla = value.get('sla')
        if sla:
            sla = str(sla).strip()
            clean = re.sub(r'<[^>]*>?', '', sla)
            match = re.match(r'^([0-9]+(?:\.[0-9]+)?)\s*%?$', clean)
            if clean != sla or not match:
                raise serializers.ValidationError("Invalid SLA Targets format. Must be a percentage value.")
            pct = float(match.group(1))
            if pct < 0 or pct > 100:
                raise serializers.ValidationError("SLA percentage must be between 0 and 100.")
                
        rto = value.get('rto')
        if rto:
            rto = str(rto).strip()
            clean = re.sub(r'<[^>]*>?', '', rto)
            if clean != rto or not re.match(r'^[0-9a-zA-Z\s\-\+]+$', clean):
                raise serializers.ValidationError("Invalid RTO format. Script/HTML characters are not allowed.")
                
        rpo = value.get('rpo')
        if rpo:
            rpo = str(rpo).strip()
            clean = re.sub(r'<[^>]*>?', '', rpo)
            if clean != rpo or not re.match(r'^[0-9a-zA-Z\s\-\+]+$', clean):
                raise serializers.ValidationError("Invalid RPO format. Script/HTML characters are not allowed.")
                
        return value

