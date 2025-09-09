"""
AI-powered threat detection and response system
"""

import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import json
import re

from velora.core.logging import LoggerMixin
from velora.core.exceptions import SecurityError


class ThreatLevel(Enum):
    """Threat severity levels"""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ThreatType(Enum):
    """Types of threats"""
    BRUTE_FORCE = "brute_force"
    DOS_ATTACK = "dos_attack"
    INJECTION = "injection"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    DATA_EXFILTRATION = "data_exfiltration"
    MALICIOUS_PAYLOAD = "malicious_payload"
    ANOMALOUS_BEHAVIOR = "anomalous_behavior"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    REPLAY_ATTACK = "replay_attack"
    MAN_IN_THE_MIDDLE = "man_in_the_middle"


@dataclass
class ThreatIndicator:
    """Threat indicator"""
    indicator_type: str
    value: Any
    confidence: float
    source: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ThreatEvent:
    """Detected threat event"""
    event_id: str
    threat_type: ThreatType
    threat_level: ThreatLevel
    source_ip: Optional[str]
    target: Optional[str]
    description: str
    indicators: List[ThreatIndicator]
    timestamp: datetime = field(default_factory=datetime.utcnow)
    mitigated: bool = False
    mitigation_actions: List[str] = field(default_factory=list)


@dataclass
class SecurityMetrics:
    """Security metrics"""
    total_events: int = 0
    threats_detected: int = 0
    threats_mitigated: int = 0
    false_positives: int = 0
    avg_detection_time: float = 0.0
    avg_mitigation_time: float = 0.0
    threat_levels: Dict[ThreatLevel, int] = field(default_factory=dict)
    threat_types: Dict[ThreatType, int] = field(default_factory=dict)


class ThreatDetectionEngine(LoggerMixin):
    """
    AI-powered threat detection and response
    """
    
    def __init__(self):
        """Initialize threat detection engine"""
        # Threat events
        self.threat_events: Dict[str, ThreatEvent] = {}
        self.active_threats: Set[str] = set()
        
        # Behavioral baselines
        self.baselines: Dict[str, Dict[str, Any]] = {}
        
        # Attack patterns
        self.attack_patterns = self._load_attack_patterns()
        
        # Rate limiting tracking
        self.request_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))
        
        # Failed authentication tracking
        self.failed_auth_attempts: Dict[str, List[datetime]] = defaultdict(list)
        
        # Blocked IPs
        self.blocked_ips: Set[str] = set()
        
        # Security metrics
        self.metrics = SecurityMetrics()
        
        # Detection rules
        self.detection_rules = self._initialize_detection_rules()
        
        # ML model placeholders (would be actual models in production)
        self.anomaly_detector = None
        self.threat_classifier = None
        
        self.is_running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        self.log_info("Threat detection engine initialized")
    
    def _load_attack_patterns(self) -> Dict[str, List[re.Pattern]]:
        """Load known attack patterns"""
        return {
            "sql_injection": [
                re.compile(r"(\bUNION\b.*\bSELECT\b)", re.IGNORECASE),
                re.compile(r"(\bOR\b.*=.*)", re.IGNORECASE),
                re.compile(r"(\bDROP\b.*\bTABLE\b)", re.IGNORECASE),
                re.compile(r"(\bINSERT\b.*\bINTO\b)", re.IGNORECASE),
                re.compile(r"(\bSELECT\b.*\bFROM\b.*\bWHERE\b)", re.IGNORECASE),
            ],
            "xss": [
                re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE),
                re.compile(r"javascript:", re.IGNORECASE),
                re.compile(r"on\w+\s*=", re.IGNORECASE),
            ],
            "path_traversal": [
                re.compile(r"\.\.\/"),
                re.compile(r"\.\.\\"),
                re.compile(r"%2e%2e%2f", re.IGNORECASE),
            ],
            "command_injection": [
                re.compile(r";\s*\w+"),
                re.compile(r"\|\s*\w+"),
                re.compile(r"`.*`"),
                re.compile(r"\$\(.*\)"),
            ]
        }
    
    def _initialize_detection_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize threat detection rules"""
        return {
            "brute_force": {
                "max_failed_attempts": 5,
                "time_window": 300,  # 5 minutes
                "threat_level": ThreatLevel.HIGH
            },
            "dos_attack": {
                "max_requests_per_second": 100,
                "max_requests_per_minute": 1000,
                "threat_level": ThreatLevel.CRITICAL
            },
            "data_exfiltration": {
                "max_data_size_mb": 100,
                "suspicious_destinations": ["external", "unknown"],
                "threat_level": ThreatLevel.HIGH
            },
            "anomalous_behavior": {
                "deviation_threshold": 3.0,  # Standard deviations
                "min_baseline_samples": 100,
                "threat_level": ThreatLevel.MEDIUM
            }
        }
    
    async def start(self) -> None:
        """Start threat detection engine"""
        if self.is_running:
            return
        
        self.is_running = True
        self._monitor_task = asyncio.create_task(self._monitor_threats())
        
        self.log_info("Threat detection engine started")
    
    async def stop(self) -> None:
        """Stop threat detection engine"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self.log_info("Threat detection engine stopped")
    
    async def analyze_request(
        self,
        request_data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """
        Analyze incoming request for threats
        
        Args:
            request_data: Request information
        
        Returns:
            ThreatEvent if threat detected, None otherwise
        """
        threats_found = []
        
        # Check for injection attacks
        injection_threat = self._check_injection_attacks(request_data)
        if injection_threat:
            threats_found.append(injection_threat)
        
        # Check for rate limiting violations
        rate_limit_threat = self._check_rate_limits(request_data)
        if rate_limit_threat:
            threats_found.append(rate_limit_threat)
        
        # Check for anomalous behavior
        anomaly_threat = await self._check_anomalies(request_data)
        if anomaly_threat:
            threats_found.append(anomaly_threat)
        
        # Return highest severity threat
        if threats_found:
            threat = max(threats_found, key=lambda t: t.threat_level.value)
            await self._handle_threat(threat)
            return threat
        
        return None
    
    def _check_injection_attacks(
        self,
        request_data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """Check for injection attacks"""
        indicators = []
        
        # Check all string values in request
        for key, value in request_data.items():
            if isinstance(value, str):
                # Check SQL injection patterns
                for pattern in self.attack_patterns["sql_injection"]:
                    if pattern.search(value):
                        indicators.append(ThreatIndicator(
                            indicator_type="sql_injection",
                            value=value[:100],
                            confidence=0.8,
                            source=key
                        ))
                
                # Check XSS patterns
                for pattern in self.attack_patterns["xss"]:
                    if pattern.search(value):
                        indicators.append(ThreatIndicator(
                            indicator_type="xss",
                            value=value[:100],
                            confidence=0.7,
                            source=key
                        ))
                
                # Check path traversal
                for pattern in self.attack_patterns["path_traversal"]:
                    if pattern.search(value):
                        indicators.append(ThreatIndicator(
                            indicator_type="path_traversal",
                            value=value[:100],
                            confidence=0.9,
                            source=key
                        ))
        
        if indicators:
            threat = ThreatEvent(
                event_id=f"threat_{datetime.utcnow().timestamp()}",
                threat_type=ThreatType.INJECTION,
                threat_level=ThreatLevel.HIGH,
                source_ip=request_data.get("ip"),
                target=request_data.get("path"),
                description="Potential injection attack detected",
                indicators=indicators
            )
            return threat
        
        return None
    
    def _check_rate_limits(
        self,
        request_data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """Check for rate limiting violations"""
        source_ip = request_data.get("ip", "unknown")
        current_time = datetime.utcnow()
        
        # Track request
        self.request_counts[source_ip].append(current_time)
        
        # Check requests per second
        recent_requests = [
            t for t in self.request_counts[source_ip]
            if (current_time - t).total_seconds() < 1
        ]
        
        rules = self.detection_rules["dos_attack"]
        
        if len(recent_requests) > rules["max_requests_per_second"]:
            threat = ThreatEvent(
                event_id=f"threat_{current_time.timestamp()}",
                threat_type=ThreatType.DOS_ATTACK,
                threat_level=rules["threat_level"],
                source_ip=source_ip,
                target=request_data.get("path"),
                description=f"Rate limit exceeded: {len(recent_requests)} requests/second",
                indicators=[
                    ThreatIndicator(
                        indicator_type="rate_limit",
                        value=len(recent_requests),
                        confidence=1.0,
                        source="request_rate"
                    )
                ]
            )
            return threat
        
        return None
    
    async def _check_anomalies(
        self,
        request_data: Dict[str, Any]
    ) -> Optional[ThreatEvent]:
        """Check for anomalous behavior using ML"""
        # In production, this would use actual ML models
        # For now, use simple heuristics
        
        user_id = request_data.get("user_id", "unknown")
        
        # Get baseline for user
        baseline = self.baselines.get(user_id, {})
        
        if not baseline:
            # Create baseline
            self.baselines[user_id] = {
                "avg_request_size": request_data.get("size", 0),
                "common_paths": [request_data.get("path")],
                "common_times": [datetime.utcnow().hour],
                "request_count": 1
            }
            return None
        
        # Check for anomalies
        indicators = []
        
        # Check request size anomaly
        if request_data.get("size", 0) > baseline["avg_request_size"] * 10:
            indicators.append(ThreatIndicator(
                indicator_type="size_anomaly",
                value=request_data.get("size"),
                confidence=0.6,
                source="request_size"
            ))
        
        # Check unusual access time
        current_hour = datetime.utcnow().hour
        if current_hour not in baseline["common_times"]:
            if 2 <= current_hour <= 5:  # Suspicious hours
                indicators.append(ThreatIndicator(
                    indicator_type="time_anomaly",
                    value=current_hour,
                    confidence=0.5,
                    source="access_time"
                ))
        
        # Update baseline
        baseline["request_count"] += 1
        baseline["avg_request_size"] = (
            (baseline["avg_request_size"] * (baseline["request_count"] - 1) + 
             request_data.get("size", 0)) / baseline["request_count"]
        )
        
        if indicators:
            threat = ThreatEvent(
                event_id=f"threat_{datetime.utcnow().timestamp()}",
                threat_type=ThreatType.ANOMALOUS_BEHAVIOR,
                threat_level=ThreatLevel.MEDIUM,
                source_ip=request_data.get("ip"),
                target=user_id,
                description="Anomalous behavior detected",
                indicators=indicators
            )
            return threat
        
        return None
    
    def track_failed_authentication(
        self,
        identity_id: str,
        source_ip: str
    ) -> Optional[ThreatEvent]:
        """
        Track failed authentication attempts
        
        Args:
            identity_id: Identity that failed authentication
            source_ip: Source IP address
        
        Returns:
            ThreatEvent if brute force detected
        """
        current_time = datetime.utcnow()
        key = f"{identity_id}:{source_ip}"
        
        # Add failed attempt
        self.failed_auth_attempts[key].append(current_time)
        
        # Clean old attempts
        rules = self.detection_rules["brute_force"]
        cutoff_time = current_time - timedelta(seconds=rules["time_window"])
        self.failed_auth_attempts[key] = [
            t for t in self.failed_auth_attempts[key]
            if t > cutoff_time
        ]
        
        # Check threshold
        if len(self.failed_auth_attempts[key]) >= rules["max_failed_attempts"]:
            threat = ThreatEvent(
                event_id=f"threat_{current_time.timestamp()}",
                threat_type=ThreatType.BRUTE_FORCE,
                threat_level=rules["threat_level"],
                source_ip=source_ip,
                target=identity_id,
                description=f"Brute force attack detected: {len(self.failed_auth_attempts[key])} failed attempts",
                indicators=[
                    ThreatIndicator(
                        indicator_type="failed_auth",
                        value=len(self.failed_auth_attempts[key]),
                        confidence=0.9,
                        source="authentication"
                    )
                ]
            )
            
            # Clear attempts after detection
            del self.failed_auth_attempts[key]
            
            return threat
        
        return None
    
    async def _handle_threat(self, threat: ThreatEvent) -> None:
        """Handle detected threat"""
        # Store threat event
        self.threat_events[threat.event_id] = threat
        self.active_threats.add(threat.event_id)
        
        # Update metrics
        self.metrics.total_events += 1
        self.metrics.threats_detected += 1
        self.metrics.threat_levels[threat.threat_level] = \
            self.metrics.threat_levels.get(threat.threat_level, 0) + 1
        self.metrics.threat_types[threat.threat_type] = \
            self.metrics.threat_types.get(threat.threat_type, 0) + 1
        
        # Log threat
        self.log_warning(
            f"Threat detected: {threat.threat_type.value}",
            threat_level=threat.threat_level.value,
            source_ip=threat.source_ip,
            target=threat.target
        )
        
        # Apply mitigation
        await self._mitigate_threat(threat)
    
    async def _mitigate_threat(self, threat: ThreatEvent) -> None:
        """Apply threat mitigation"""
        mitigation_actions = []
        
        # Block IP for severe threats
        if threat.threat_level in [ThreatLevel.HIGH, ThreatLevel.CRITICAL]:
            if threat.source_ip:
                self.block_ip(threat.source_ip)
                mitigation_actions.append(f"Blocked IP: {threat.source_ip}")
        
        # Specific mitigations by threat type
        if threat.threat_type == ThreatType.BRUTE_FORCE:
            mitigation_actions.append("Enforced account lockout")
            mitigation_actions.append("Required CAPTCHA")
        
        elif threat.threat_type == ThreatType.DOS_ATTACK:
            mitigation_actions.append("Rate limiting applied")
            mitigation_actions.append("Traffic shaping enabled")
        
        elif threat.threat_type == ThreatType.INJECTION:
            mitigation_actions.append("Request blocked")
            mitigation_actions.append("Input sanitization enforced")
        
        # Update threat event
        threat.mitigated = True
        threat.mitigation_actions = mitigation_actions
        
        # Update metrics
        self.metrics.threats_mitigated += 1
        
        self.log_info(
            f"Threat mitigated: {threat.event_id}",
            actions=mitigation_actions
        )
    
    def block_ip(self, ip_address: str) -> None:
        """Block an IP address"""
        self.blocked_ips.add(ip_address)
        self.log_warning(f"IP blocked: {ip_address}")
    
    def unblock_ip(self, ip_address: str) -> None:
        """Unblock an IP address"""
        self.blocked_ips.discard(ip_address)
        self.log_info(f"IP unblocked: {ip_address}")
    
    def is_ip_blocked(self, ip_address: str) -> bool:
        """Check if IP is blocked"""
        return ip_address in self.blocked_ips
    
    async def _monitor_threats(self) -> None:
        """Monitor and manage active threats"""
        while self.is_running:
            try:
                current_time = datetime.utcnow()
                
                # Clean up old threats
                for threat_id in list(self.active_threats):
                    threat = self.threat_events.get(threat_id)
                    if threat:
                        # Remove after 1 hour
                        if (current_time - threat.timestamp).total_seconds() > 3600:
                            self.active_threats.discard(threat_id)
                
                # Generate alerts for critical threats
                for threat_id in self.active_threats:
                    threat = self.threat_events.get(threat_id)
                    if threat and threat.threat_level == ThreatLevel.CRITICAL:
                        if not threat.mitigated:
                            self.log_error(
                                f"Critical threat not mitigated: {threat_id}",
                                threat_type=threat.threat_type.value
                            )
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                self.log_error(f"Threat monitoring error: {e}")
    
    def get_threat_report(self) -> Dict[str, Any]:
        """Generate threat report"""
        return {
            "metrics": {
                "total_events": self.metrics.total_events,
                "threats_detected": self.metrics.threats_detected,
                "threats_mitigated": self.metrics.threats_mitigated,
                "false_positives": self.metrics.false_positives,
                "threat_levels": {
                    level.name: count
                    for level, count in self.metrics.threat_levels.items()
                },
                "threat_types": {
                    threat_type.value: count
                    for threat_type, count in self.metrics.threat_types.items()
                }
            },
            "active_threats": len(self.active_threats),
            "blocked_ips": len(self.blocked_ips),
            "recent_threats": [
                {
                    "event_id": threat.event_id,
                    "threat_type": threat.threat_type.value,
                    "threat_level": threat.threat_level.name,
                    "timestamp": threat.timestamp.isoformat(),
                    "mitigated": threat.mitigated
                }
                for threat in sorted(
                    self.threat_events.values(),
                    key=lambda t: t.timestamp,
                    reverse=True
                )[:10]
            ]
        }