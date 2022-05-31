from datetime import datetime, timezone
import calendar

def get_unix_time():
    # get the current utc time
    t = datetime.now(timezone.utc)

    unixtime = calendar.timegm(t.utctimetuple())

    # print the unix timestamp
    print(unixtime)

if __name__ == '__main__':
    get_unix_time()
