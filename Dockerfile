FROM python:3.5-alpine
COPY . /code
WORKDIR /code
RUN python setup.py install
RUN pip install gunicorn
ARG SECRET_KEY=passThisAtBuildTime
ARG PORT="8910"
ARG WORKERS="4"
ARG TIMEOUT="30"
ARG STORAGE_BACKEND
ARG MONGO_HOST
ARG MONGO_PORT="27017"
ARG MONGO_DB
ARG REDIS_HOST
ARG REDIS_PORT="6379"
ARG REDIS_DB
ARG VERBOSITY="WARN"
ENV \
    IDNEST_STORAGE_BACKEND=${STORAGE_BACKEND} \
    IDNEST_SECRET_KEY=${SECRET_KEY} \
    IDNEST_MONGO_HOST=${MONGO_HOST} \
    IDNEST_MONGO_PORT=${MONGO_PORT} \ 
    IDNEST_MONBO_DB=${MONGO_DB} \
    IDNEST_REDIS_HOST=${REDIS_HOST} \
    IDNEST_REDIS_PORT=${REDIS_PORT} \
    IDNEST_REDIS_DB=${REDIS_DB} \
    IDNEST_VERBOSITY=${VERBOSITY} \
    WORKERS=${WORKERS} \
    TIMEOUT=${TIMEOUT} \
    PORT=${PORT}
CMD gunicorn idnest:app -w ${WORKERS} -t ${TIMEOUT} -b 0.0.0.0:${PORT}
