source env 2> /dev/null
if [ $? -ne 0 ];then
    . ./env # For mac environments
fi
export PYTHONPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )/src"
gunicorn --bind ${BIND_ADDRESS:="127.0.0.1:9081"} wsgi:app
