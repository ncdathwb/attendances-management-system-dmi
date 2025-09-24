"""Shared in-memory email status state.

Note: This is only a transient cache for 'sending' status and quick lookups.
The source of truth is the persistent table `email_status_records`.
"""

# request_id -> { 'status': 'sending|success|error', 'message': str, 'timestamp': float }
email_status = {}


