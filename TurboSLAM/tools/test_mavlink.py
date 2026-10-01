import math
from pymavlink import mavutil

SERIAL_PORT = '/dev/ttyTHS1'
SERIAL_BAUD = 921600
mav_conn = mavutil.mavlink_connection(
            SERIAL_PORT,
            baud=SERIAL_BAUD,
            source_system=1,
            source_component=197,   # MAV_COMP_ID_ODOMETRY
            dialect='common'
        )
mav = mav_conn.mav
print(dir(mav))
