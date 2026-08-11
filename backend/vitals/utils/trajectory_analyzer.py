"""
Phase 10: Risk Trajectory Analyzer

Analyzes projected vital sign trajectories to determine:
- When patient will reach critical threshold
- Rate of deterioration
- Recommended intervention window
- Predictive risk levels
"""

from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class TrajectoryAnalyzer:
    """
    Analyzes vital sign trajectories to predict deterioration timeline.

    Takes current vitals, forecasted future values, and NEWS2 thresholds
    to determine when patient will reach critical state.
    """

    # NEWS2 critical thresholds per vital
    VITAL_THRESHOLDS = {
        'heart_rate': {
            'critical_low': 40,
            'critical_high': 130,
            'warning_low': 50,
            'warning_high': 110,
        },
        'respiratory_rate': {
            'critical_low': 8,
            'critical_high': 30,
            'warning_low': 12,
            'warning_high': 25,
        },
        'oxygen_saturation': {
            'critical': 88,
            'warning': 92,
        },
        'bp_systolic': {
            'critical_low': 90,
            'critical_high': 180,
            'warning_low': 100,
            'warning_high': 160,
        },
        'temperature': {
            'critical_low': 35,
            'critical_high': 39.5,
            'warning_low': 36,
            'warning_high': 39,
        },
    }

    def __init__(self):
        self.forecast_horizons = [24, 48, 72]  # hours

    def calculate_time_to_deterioration(
        self,
        current_vital_value: float,
        vital_name: str,
        forecast_data: Dict,
    ) -> Dict:
        """
        Calculate when vital will reach critical threshold.

        Args:
            current_vital_value: Current measured vital value
            vital_name: Name of vital (heart_rate, oxygen_saturation, etc.)
            forecast_data: Forecast output from ForecastingEngine

        Returns:
            Dictionary with time-to-critical calculations
        """
        if forecast_data.get('forecast') is None:
            return {
                'hours_to_critical': None,
                'projected_at_critical': None,
                'risk_status': 'unknown',
                'reasoning': 'Insufficient forecast data'
            }

        try:
            forecasted_value = forecast_data['forecast']
            trend = forecast_data.get('trend', {}).get('direction', 'stable')
            magnitude = forecast_data.get('trend', {}).get('magnitude', 0)

            # Get critical threshold for this vital
            thresholds = self.VITAL_THRESHOLDS.get(vital_name, {})
            if not thresholds:
                return {
                    'hours_to_critical': None,
                    'risk_status': 'unknown',
                    'reasoning': f'No thresholds defined for {vital_name}'
                }

            # Determine critical boundaries
            if vital_name == 'oxygen_saturation':
                critical_threshold = thresholds.get('critical', 88)
                warning_threshold = thresholds.get('warning', 92)
                # Already critical?
                if current_vital_value < critical_threshold:
                    return {
                        'hours_to_critical': 0,
                        'risk_status': 'critical_now',
                        'reasoning': 'Already at critical level'
                    }
                # Heading towards critical?
                deteriorating = forecasted_value < current_vital_value
            elif vital_name in ['respiratory_rate', 'heart_rate']:
                critical_high = thresholds.get('critical_high', 130)
                critical_low = thresholds.get('critical_low', 40)

                # Determine which direction patient is heading
                is_rising = magnitude > 0
                is_falling = magnitude < 0

                # Already at critical?
                if (is_rising and current_vital_value >= critical_high) or \
                   (is_falling and current_vital_value <= critical_low):
                    return {
                        'hours_to_critical': 0,
                        'risk_status': 'critical_now',
                        'reasoning': 'Already at critical level'
                    }

                # Set thresholds based on direction
                if is_rising:
                    critical_threshold = critical_high
                    deteriorating = forecasted_value > current_vital_value
                else:
                    critical_threshold = critical_low
                    deteriorating = forecasted_value < current_vital_value
            else:
                # Default for others (BP, temp)
                return {
                    'hours_to_critical': None,
                    'risk_status': 'stable',
                    'reasoning': f'Monitoring {vital_name}'
                }

            # Calculate hours to critical if deteriorating
            if deteriorating and abs(magnitude) > 0.01:
                # How many units from current position to critical threshold?
                if vital_name == 'oxygen_saturation':
                    value_delta = current_vital_value - critical_threshold  # SpO2 falling towards critical
                else:
                    value_delta = abs(critical_threshold - current_vital_value)

                if value_delta > 0.1:  # At least 0.1 units away from critical
                    # How long to reach critical at current rate?
                    hours_to_critical = value_delta / abs(magnitude)

                    # Check if will reach critical in forecast window
                    if hours_to_critical < 72:
                        return {
                            'hours_to_critical': round(hours_to_critical, 1),
                            'projected_at_critical': self._hours_from_now(hours_to_critical),
                            'risk_status': 'deteriorating_to_critical',
                            'reason': f'{vital_name} trending {trend} at {magnitude:.3f} units/hr',
                            'current_value': current_vital_value,
                            'critical_threshold': critical_threshold,
                            'forecast_24h': round(forecasted_value, 2),
                        }

            # Not deteriorating towards critical
            return {
                'hours_to_critical': None,
                'risk_status': 'stable',
                'reason': f'{vital_name} trending {trend}',
                'current_value': current_vital_value,
                'forecast_24h': round(forecasted_value, 2),
            }

        except Exception as e:
            logger.error(f"Trajectory calculation error: {e}")
            return {
                'hours_to_critical': None,
                'risk_status': 'error',
                'reasoning': str(e)
            }

    def analyze_patient_trajectory(
        self,
        current_vitals: Dict[str, float],
        forecasts: Dict[str, Dict],
    ) -> Dict:
        """
        Comprehensive trajectory analysis across all vitals.

        Returns:
            Dictionary with:
            - earliest_critical_time: When first vital reaches critical
            - vitals_at_risk: List of vitals deteriorating
            - risk_summary: Overall patient risk trajectory
            - recommendations: Clinical actions recommended
        """
        trajectories = {}
        critical_times = []

        for vital_name, current_value in current_vitals.items():
            if vital_name not in forecasts:
                continue

            trajectory = self.calculate_time_to_deterioration(
                current_value, vital_name, forecasts[vital_name]
            )
            trajectories[vital_name] = trajectory

            # Track critical times
            if trajectory.get('hours_to_critical') is not None:
                critical_times.append({
                    'vital': vital_name,
                    'hours': trajectory['hours_to_critical'],
                    'timestamp': trajectory.get('projected_at_critical'),
                    'reason': trajectory.get('reason', '')
                })

        # Sort by earliest critical time
        critical_times.sort(key=lambda x: x['hours'])

        # Summarize risk
        risk_summary = self._summarize_risk(trajectories, critical_times)

        return {
            'trajectories': trajectories,
            'earliest_critical': critical_times[0] if critical_times else None,
            'vitals_at_risk': [ct['vital'] for ct in critical_times],
            'risk_summary': risk_summary,
            'recommendations': self._generate_recommendations(critical_times, risk_summary),
            'intervention_window_hours': critical_times[0]['hours'] if critical_times else None,
        }

    def _summarize_risk(
        self,
        trajectories: Dict,
        critical_times: List[Dict],
    ) -> Dict:
        """Generate risk summary."""
        if not critical_times:
            return {
                'level': 'low',
                'description': 'All vitals stable',
                'urgency': 'routine'
            }

        earliest_hours = critical_times[0]['hours']

        if earliest_hours < 6:
            level = 'critical'
            urgency = 'immediate'
        elif earliest_hours < 24:
            level = 'high'
            urgency = 'urgent'
        elif earliest_hours < 48:
            level = 'medium'
            urgency = 'elevated'
        else:
            level = 'medium'
            urgency = 'monitor'

        return {
            'level': level,
            'description': f'Patient deterioration projected in {earliest_hours:.1f} hours',
            'urgency': urgency,
            'critical_vitals_count': len(critical_times),
        }

    def _generate_recommendations(
        self,
        critical_times: List[Dict],
        risk_summary: Dict,
    ) -> List[str]:
        """Generate clinical recommendations based on trajectory."""
        recommendations = []

        if not critical_times:
            recommendations.append("Continue routine monitoring")
            return recommendations

        earliest_hours = critical_times[0]['hours']
        affected_vitals = [ct['vital'] for ct in critical_times]

        # Urgency-based recommendations
        if earliest_hours < 6:
            recommendations.append(
                f"🚨 URGENT: {affected_vitals[0].replace('_', ' ').title()} "
                f"will reach critical level in ~{earliest_hours:.1f} hours"
            )
            recommendations.append("Immediate senior clinical review required")
            recommendations.append("Prepare for potential escalation of care")
        elif earliest_hours < 24:
            recommendations.append(
                f"⚠️ HIGH PRIORITY: Deterioration forecast within 24 hours"
            )
            recommendations.append("Schedule close monitoring (hourly or more frequent)")
            recommendations.append("Notify senior staff of deterioration trajectory")
        elif earliest_hours < 72:
            recommendations.append(
                f"📊 ATTENTION: Patient on deterioration trajectory "
                f"({', '.join(affected_vitals[:2])})"
            )
            recommendations.append("Increase monitoring frequency to 4-6 hourly")
            recommendations.append("Review care plan and preventive measures")

        # Vital-specific actions
        if 'oxygen_saturation' in affected_vitals:
            recommendations.append("Review respiratory support (oxygen therapy)")
        if 'heart_rate' in affected_vitals:
            recommendations.append("Check cardiovascular medication/hydration")
        if 'respiratory_rate' in affected_vitals:
            recommendations.append("Assess for respiratory distress indicators")

        recommendations.append(
            f"Intervention window: {earliest_hours:.1f} hours to prevent critical state"
        )

        return recommendations

    def _hours_from_now(self, hours: float) -> str:
        """Convert hours to human-readable future timestamp."""
        future_time = datetime.now() + timedelta(hours=hours)
        return future_time.strftime("%Y-%m-%d %H:%M")

    def get_risk_trajectory_graph_data(
        self,
        current_vitals: Dict[str, float],
        forecasts: Dict[str, Dict],
        horizon_hours: int = 48,
    ) -> Dict:
        """
        Generate data for visualizing risk trajectory over time.

        Returns data suitable for charting current vs. projected risk.
        """
        time_points = [0, 6, 12, 24, 36, 48]
        trajectory_data = {}

        for vital_name in current_vitals.keys():
            if vital_name not in forecasts:
                continue

            forecast = forecasts[vital_name]
            trajectory_data[vital_name] = {
                'current': current_vitals[vital_name],
                'forecast_24h': forecast.get('forecast'),
                'trend': forecast.get('trend', {}).get('direction'),
                'critical_threshold': self.VITAL_THRESHOLDS.get(vital_name, {}).get('critical'),
            }

        return {
            'time_points': time_points,
            'vital_trajectories': trajectory_data,
            'projection_hours': horizon_hours,
        }
