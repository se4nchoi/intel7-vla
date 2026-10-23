"""Create a fresh viewer stream after a previous viewer has been closed."""
import logging
from uuid import uuid4
import rerun as rr


def fresh_stream():
    old = rr.get_global_data_recording()
    if old is not None:
        try:
            old.disconnect()
        except RuntimeError:
            logging.warning('Previous Rerun viewer disconnected; replacing its stream')
    # rr.init flushes orphaned streams; a severed old gRPC connection can make
    # that cleanup raise before a new stream exists. Use the public stream API.
    return rr.RecordingStream('LeRobot live', recording_id=uuid4(), make_default=True)
