from collections import defaultdict

transactionNamings = {
    "VISIT_CREATE": "NOVBE YARADILDI",
    "VISIT_CALL": "ÇAĞIRILDI",
    "VISIT_TRANSFER_TO_QUEUE": "transfer",
    "VISIT_TRANSFER_TO_SERVICE_POINT_POOL": "transfer",
    "VISIT_TRANSFER_TO_USER_POOL": "park",
    "VISIT_END": "basha catdi",
    "VISIT_NOSHOW": "vetendas gelmedi",
    "VISIT_REMOVE": "silindi",
    "VISIT_RECYCLE": "yeninden novbeye qaytarildi",
}

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


def convert_data_to_json(data):
    """
    Processes flat SQL rows into a structured JSON format pairing Start/End events.
    Output is flattened where each event in the flow becomes a separate object.
    """
    STARTERS = {'VISIT_CREATE', 'VISIT_CALL'}
    ENDERS = {
        'VISIT_TRANSFER_TO_QUEUE', 'VISIT_TRANSFER_TO_SERVICE_POINT_POOL',
        'VISIT_TRANSFER_TO_USER_POOL', 'VISIT_END', 'VISIT_NOSHOW',
        'VISIT_REMOVE', 'VISIT_RECYCLE'
    }

    # 1. Group data by transaction ID (fvt.id)
    grouped_data = defaultdict(lambda: {
        'meta': {},
        'notes': [],
        'events': []
    })

    for row in data:
        tx_id = row['id']

        # Initialize Meta data
        if not grouped_data[tx_id]['meta']:
            grouped_data[tx_id]['meta'] = {
                'id': tx_id,
                'create_timestamp': row.get('create_timestamp'),
                'waiting_time': row.get('waiting_time'),
                'call_timestamp': row.get('call_timestamp'),
                'transaction_time': row.get('transaction_time'),
                'outcome_key': row.get('outcome_key'),
                'staff': {
                    'first_name': row.get('first_name'),
                    'last_name': row.get('last_name'),
                    'name': row.get('name')
                }
            }

        # Collect Notes
        note_entry = {
            'content': row.get('note'),
            'status': row.get('status'),
            'table': row.get('table')
        }
        if note_entry['content'] is not None:
            exists = any(
                n['content'] == note_entry['content'] and
                n['status'] == note_entry['status']
                for n in grouped_data[tx_id]['notes']
            )
            if not exists:
                grouped_data[tx_id]['notes'].append(note_entry)

        # Collect Events
        if row.get('operation'):
            grouped_data[tx_id]['events'].append({
                'operation': row.get('operation'),
                'event_timestamp': row.get('event_timestamp')
            })

    # 2. Process Events to generate the correct 'Flow' and Flatten Output
    result = []

    for tx_id, group in grouped_data.items():
        # Sort events by timestamp
        sorted_events = sorted(group['events'], key=lambda x: x['event_timestamp'])

        processed_flow = []
        i = 0
        n = len(sorted_events)

        while i < n:
            curr_event = sorted_events[i]
            op_name = curr_event['operation']

            # Ignore irrelevant operations
            if op_name not in STARTERS and op_name not in ENDERS:
                i += 1
                continue

            # If we encounter an orphaned ender (should be consumed by a Call), skip it
            if op_name in ENDERS:
                i += 1
                continue

            # Logic for VISIT_CREATE
            if op_name == 'VISIT_CREATE':
                processed_flow.append({
                    "operation": "VISIT_CREATE",
                    "event_timestamp": curr_event['event_timestamp']
                })
                i += 1

            # Logic for VISIT_CALL
            elif op_name == 'VISIT_CALL':
                # Look ahead to find the next relevant event
                next_idx = -1
                for j in range(i + 1, n):
                    next_op = sorted_events[j]['operation']
                    if next_op in STARTERS or next_op in ENDERS:
                        next_idx = j
                        break

                call_entry = {
                    "operation": "VISIT_CALL",
                    "start_timestamp": curr_event['event_timestamp']
                }

                if next_idx != -1:
                    next_event = sorted_events[next_idx]

                    # Scenario A: Followed by an Ender (Normal Flow)
                    if next_event['operation'] in ENDERS:
                        call_entry['operation_end'] = next_event['operation']
                        call_entry['end_timestamp'] = next_event['event_timestamp']
                        processed_flow.append(call_entry)
                        i = next_idx + 1  # Skip the ender, it's consumed

                    # Scenario B: Followed by another VISIT_CALL (Recall / Interrupted Flow)
                    elif next_event['operation'] == 'VISIT_CALL':
                        call_entry['operation_end'] = None
                        call_entry['end_timestamp'] = None
                        processed_flow.append(call_entry)
                        i += 1  # Move to next call, don't consume it yet

                    else:
                        # Fallback for unexpected starters
                        call_entry['operation_end'] = None
                        call_entry['end_timestamp'] = None
                        processed_flow.append(call_entry)
                        i += 1
                else:
                    # No next event, dangling call
                    call_entry['operation_end'] = None
                    call_entry['end_timestamp'] = None
                    processed_flow.append(call_entry)
                    i += 1

        # Construct the flattened result objects
        meta = group['meta']

        # Prepare common base data
        base_item = {
            "id": meta['id'],
            "create_timestamp": meta['create_timestamp'],
            "waiting_time": meta['waiting_time'],
            "call_timestamp": meta['call_timestamp'],
            "transaction_time": meta['transaction_time'],
            "outcome_key": meta['outcome_key'],
            # Flatten staff fields
            "first_name": meta['staff']['first_name'],
            "last_name": meta['staff']['last_name'],
            "name": meta['staff']['name'],
        }

        # Determine note content (singular object or null)
        note_data = group['notes'][0] if group['notes'] else None

        # Iterate through processed flow to create individual entries
        for flow_event in processed_flow:
            new_item = base_item.copy()
            new_item['note'] = note_data
            # Merge flow specific keys (operation, event_timestamp, start_timestamp, etc.)
            new_item.update(flow_event)
            result.append(new_item)

    return result