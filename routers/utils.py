from database.models import DbEndpoint
from sqlalchemy.orm import Session
from typing import Union
from sqlalchemy.orm import joinedload
from routers.schemas import Application

def get_endpoint_status_ratio(endpoint_uid: int, db: Session) -> Union[dict, float]:
    endpoint = db.query(DbEndpoint).filter(DbEndpoint.uid == endpoint_uid).first()
    
    if endpoint:
        total_logs = len(endpoint.log)
        stable_count = unstable_count = downtime_count = 0
        last_10_statuses = [log.status for log in endpoint.log[-10:]]
        
        if all(status in ['200', '307'] for status in last_10_statuses):
            stable_count = total_logs
        elif all(status not in ['200', '307'] for status in last_10_statuses):
            unstable_count = total_logs
        else:
            is_downtime = False
            for log in endpoint.log:
                if log.status == 'Stable':
                    stable_count += 1
                    if is_downtime:
                        downtime_count += 1
                        is_downtime = False
                elif log.status == 'Unstable':
                    unstable_count += 1
                    if is_downtime:
                        downtime_count += 1
                        is_downtime = False
                else:
                    if not is_downtime:
                        is_downtime = True
        
        return {
            'down': downtime_count / total_logs,
            'stable': stable_count / total_logs,
            'unstable': unstable_count / total_logs
        }
    else:
        return {
            'error': 'Endpoint not found'
        }
        
def determine_stability(endpointId: int, db: Session):
    endpoint = db.query(DbEndpoint).options(joinedload(DbEndpoint.log)).filter(DbEndpoint.uid == endpointId).first()
    if endpoint:
        log_statuses = [log.status for log in endpoint.log[-10:]] 
        print(log_statuses)
        if all(status in ['200', '302'] for status in log_statuses):
            return "Stable"
        elif all(status not in ['200', '302'] for status in log_statuses):
            return "Down"
        else:
            return "Unstable"
    else:
        return "Endpoint not found"
    
def calculate_downtime_minutes(app: Application) -> float:
    total_downtime = 0.0
    
    for endpoint in app.endpoints:
        for log in endpoint.log:
            if log.status != '200' or log.status != '302':
                total_downtime = total_downtime + 1 
                
    
    return total_downtime * app.refreshInterval

def time_to_seconds(time_str: str) -> int:
    parts = time_str.split()
    if len(parts) != 2:
        raise ValueError("Invalid time format. Expected format: 'X sec' or 'Y min'")
    value, unit = int(parts[0]), parts[1].lower()
    if unit == 'sec':
        return value
    elif unit == 'min':
        return value * 60
    elif unit == 'hours':
        return value * 60 * 60
    elif unit == 'days':
        return value * 60 * 60 * 24
    elif unit == 'day':
        return value * 60 * 60 * 24
    else:
        raise ValueError("Invalid time unit. Expected 'sec' or 'min'")