from datetime import datetime
from constants import TIMESTAMP_FORMAT, KEY_TIMESTAMP


def datetimeSerializer(obj):
    if isinstance(obj, datetime):
        return obj.strftime(TIMESTAMP_FORMAT)
    raise TypeError("Type %s not serializable" % type(obj))


def datetimeDeserializer(jsonDict):
    for k, v in jsonDict.items():
        if k == KEY_TIMESTAMP:
            jsonDict[k] = datetime.strptime(v, TIMESTAMP_FORMAT)
    return jsonDict
