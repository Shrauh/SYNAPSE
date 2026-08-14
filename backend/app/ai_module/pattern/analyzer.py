"""
SYNAPSE Pattern Analyzer — Recurring Failure & Architectural Recommendation.

Analyzes incident history to detect recurring fault patterns (L4).
When the same root cause appears repeatedly, generates architectural
recommendations instead of just restarting pods.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import numpy as np


@dataclass
class RecurringPattern:
    """A detected recurring failure pattern."""
    root_cause_service: str
    occurrence_count: int
    first_seen: str
    last_seen: str
    common_fault_types: List[str]
    avg_resolution_time_ms: float
    severity_trend: str  # 'stable', 'worsening', 'improving'


@dataclass
class ArchRecommendation:
    """An architectural recommendation for a recurring issue."""
    service: str
    problem: str
    recommendation: str
    estimated_effort: str  # 'low', 'medium', 'high'
    priority: str  # 'critical', 'high', 'medium', 'low'
    evidence: str


class PatternAnalyzer:
    """Detects recurring failure patterns and generates architectural recommendations.
    
    Maintains an in-memory incident log and analyzes it to:
    1. Find services that fail repeatedly (same root cause > 3 times)
    2. Identify the common fault types for each recurring service
    3. Generate actionable architectural recommendations
    """
    
    # Knowledge base: fault type -> architectural recommendation
    RECOMMENDATION_KB = {
        'memory_leak': {
            'recommendation': 'Investigate memory leaks in application code. Consider upgrading to a newer runtime with improved GC. Add memory-based HPA autoscaling and set explicit memory limits.',
            'effort': 'medium',
            'priority': 'high',
        },
        'latency_spike': {
            'recommendation': 'Add connection pooling and request timeouts. Implement circuit breaker pattern with Istio. Consider caching frequently accessed data. Review database query performance.',
            'effort': 'medium',
            'priority': 'high',
        },
        'cpu_overload': {
            'recommendation': 'Profile CPU-intensive code paths. Add CPU-based HPA autoscaling. Consider splitting compute-heavy operations into async background jobs.',
            'effort': 'medium',
            'priority': 'high',
        },
        'error_spike': {
            'recommendation': 'Implement retry logic with exponential backoff. Add input validation and error boundaries. Review error handling in dependent service calls. Add circuit breaker for downstream dependencies.',
            'effort': 'low',
            'priority': 'critical',
        },
        'connection_timeout': {
            'recommendation': 'Increase connection pool size. Add health checks for dependent services. Implement connection retry with backoff. Consider service mesh timeout policies.',
            'effort': 'low',
            'priority': 'high',
        },
        'cascading_failure': {
            'recommendation': 'Implement bulkhead pattern to isolate failures. Add circuit breakers between services. Set up rate limiting at ingress. Review service dependency chain for single points of failure.',
            'effort': 'high',
            'priority': 'critical',
        },
    }
    
    DEFAULT_RECOMMENDATION = {
        'recommendation': 'Investigate recurring failures in this service. Review recent deployments, configuration changes, and infrastructure health. Consider adding more comprehensive monitoring and alerting.',
        'effort': 'medium',
        'priority': 'medium',
    }
    
    def __init__(self):
        """Initialize the pattern analyzer with an empty incident log."""
        self._incidents: List[Dict[str, Any]] = []
    
    def record_incident(
        self, 
        root_cause_service: str, 
        fault_type: Optional[str] = None, 
        severity_level: int = 1, 
        resolution_time_ms: float = 0.0, 
        resolved: bool = False
    ) -> None:
        """Record a resolved incident for pattern analysis.
        
        Args:
            root_cause_service: The identified root cause service.
            fault_type: The type of fault.
            severity_level: The severity level of the incident.
            resolution_time_ms: Time taken to resolve the incident in ms.
            resolved: Whether the incident was successfully resolved.
        """
        self._incidents.append({
            'root_cause': root_cause_service,
            'fault_type': fault_type or 'unknown',
            'severity': severity_level,
            'resolution_time_ms': resolution_time_ms,
            'resolved': resolved,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        })
    
    def detect_recurring(self, window_days: int = 30) -> List[RecurringPattern]:
        """Detect recurring failure patterns within the given time window.
        
        Args:
            window_days: Number of days to look back for recurring patterns.
            
        Returns:
            A list of detected recurring patterns.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        recent = [i for i in self._incidents if i['timestamp'] >= cutoff.isoformat()]
        
        # Count occurrences per root cause
        root_counts = Counter(i['root_cause'] for i in recent)
        
        patterns = []
        for service, count in root_counts.items():
            if count < 2:
                continue
            
            service_incidents = [i for i in recent if i['root_cause'] == service]
            fault_types = [i['fault_type'] for i in service_incidents]
            fault_counter = Counter(fault_types)
            
            timestamps = sorted([i['timestamp'] for i in service_incidents])
            resolution_times = [i['resolution_time_ms'] for i in service_incidents if i['resolution_time_ms'] > 0]
            
            # Determine severity trend
            severities = [i['severity'] for i in service_incidents]
            if len(severities) >= 3:
                recent_avg = np.mean(severities[-3:])
                old_avg = np.mean(severities[:3])
                if recent_avg > old_avg + 0.5:
                    trend = 'worsening'
                elif recent_avg < old_avg - 0.5:
                    trend = 'improving'
                else:
                    trend = 'stable'
            else:
                trend = 'stable'
            
            patterns.append(RecurringPattern(
                root_cause_service=service,
                occurrence_count=count,
                first_seen=timestamps[0],
                last_seen=timestamps[-1],
                common_fault_types=[ft for ft, _ in fault_counter.most_common(3)],
                avg_resolution_time_ms=np.mean(resolution_times) if resolution_times else 0.0,
                severity_trend=trend,
            ))
        
        # Sort by count descending
        patterns.sort(key=lambda p: p.occurrence_count, reverse=True)
        return patterns
    
    def generate_recommendations(
        self, 
        patterns: Optional[List[RecurringPattern]] = None
    ) -> List[ArchRecommendation]:
        """Generate architectural recommendations from recurring patterns.
        
        Args:
            patterns: Optional list of pre-computed recurring patterns.
            
        Returns:
            A list of architectural recommendations.
        """
        if patterns is None:
            patterns = self.detect_recurring()
        
        recommendations = []
        for pattern in patterns:
            if pattern.occurrence_count < 3:
                continue  # Only recommend for truly recurring issues
            
            # Find best matching recommendation from KB
            primary_fault = pattern.common_fault_types[0] if pattern.common_fault_types else 'unknown'
            kb_entry = self.RECOMMENDATION_KB.get(primary_fault, self.DEFAULT_RECOMMENDATION)
            
            evidence = (f"{pattern.root_cause_service} has failed {pattern.occurrence_count} times. "
                       f"Most common fault: {primary_fault}. "
                       f"Trend: {pattern.severity_trend}. "
                       f"Avg resolution: {pattern.avg_resolution_time_ms:.0f}ms.")
            
            recommendations.append(ArchRecommendation(
                service=pattern.root_cause_service,
                problem=f"Recurring {primary_fault} ({pattern.occurrence_count} incidents)",
                recommendation=kb_entry['recommendation'],
                estimated_effort=kb_entry['effort'],
                priority='critical' if pattern.severity_trend == 'worsening' else kb_entry['priority'],
                evidence=evidence,
            ))
        
        return recommendations
    
    def get_recurring_patterns(self, window_days: int = 30) -> List[Dict[str, Any]]:
        """Return recurring patterns formatted as dicts."""
        patterns = self.detect_recurring(window_days=window_days)
        return [
            {
                "service": p.root_cause_service,
                "root_cause": p.root_cause_service,
                "count": p.occurrence_count,
                "occurrences": p.occurrence_count,
                "fault_types": p.common_fault_types,
                "severity_trend": p.severity_trend,
            }
            for p in patterns
        ]

    def get_recommendations(self) -> List[Dict[str, Any]]:
        """Return architectural recommendations as dicts."""
        recs = self.generate_recommendations()
        return [
            {
                "service": r.service,
                "problem": r.problem,
                "recommendation": r.recommendation,
                "priority": r.priority,
                "effort": r.estimated_effort,
                "evidence": r.evidence,
            }
            for r in recs
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all patterns and recommendations.
        
        Returns:
            Dictionary containing summary statistics and top recommendations.
        """
        patterns = self.detect_recurring()
        recommendations = self.generate_recommendations(patterns)
        return {
            'total_incidents': len(self._incidents),
            'recurring_patterns': len(patterns),
            'recommendations': len(recommendations),
            'patterns': [{'service': p.root_cause_service, 'count': p.occurrence_count, 'trend': p.severity_trend} for p in patterns],
            'top_recommendations': [{'service': r.service, 'problem': r.problem, 'priority': r.priority} for r in recommendations[:5]],
        }

# Module-level singleton
pattern_analyzer = PatternAnalyzer()
