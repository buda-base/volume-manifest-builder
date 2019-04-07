# volume-manifest-tool

Internal tool to create json manifests for volumes present in S3 for the IIIF presentation API server.

### Dependencies

```
pip install pillow boto3 s3transfer
```

### Use

Prepare a file listing one RID per line (no `bdr:` prefix), let's say it's on `/path/to/file` and run:

```
./manifestforwork.py /path/to/file
```

### Configuration

You need some AWS credentials in `/etc/buda/volumetool/credentials`, they must allow the user to read all files and write json files in the `archive.tbrc.org` bucket.