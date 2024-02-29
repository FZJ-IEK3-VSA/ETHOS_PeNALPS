# For Windows
docker run --rm --volume %cd%/paper:/data --env JOURNAL=joss openjournals/inara
Image Name: openjournals/inara
Volume path: Needs to be adjusted between windows and linux


# For Linux
docker run --rm \
    --volume $PWD/paper:/data \
    --user $(id -u):$(id -g) \
    --env JOURNAL=joss \
    openjournals/inara