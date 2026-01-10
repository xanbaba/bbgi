def convert_data(cursor):
    columns = [col[0] for col in cursor.description]
    data = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return data

def format_time(seconds):
    if seconds:
        seconds = int(seconds)
        hours = seconds // 3600  
        minutes = (seconds % 3600) // 60  
        remaining_seconds = seconds % 60  
        return f"{hours:02}:{minutes:02}:{remaining_seconds:02}"
    else:
        return None

def parse_time(time_string):
    if time_string:
        try:
            hours, minutes, seconds = map(int, time_string.split(':'))
            total_seconds = int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            return total_seconds 
        except ValueError:
            raise ValueError("Time string must be in 'hh:mm:ss' format")
    else:
        return None
