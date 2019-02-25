
S3BUCKET = "archive.tbrc.org"

def manifestForWork(workRID):
	"""
	this function generates the manifests for each volume of a work RID (example W22084)
	"""
	volumeInfos = getVolumeInfos(workRID)
	for vi in volumeInfos:
		manifestForVolume(workRID, vi)
	pass

def manifestForVolume(workRID, vi):
	"""
	this function generates the manifest for an image group of a work (example: I0886 in W22084)
	"""
	s3folderPrefix = getS3FolderPrefix(workRID, vi.imageGroupID)
	if manifestExists(s3folderPrefix)
		return
	manifest = generateManifest(s3folderPrefix, vi.imageList)
	uploadManifest(manifest)

def uploadManifest(s3folderPrefix, manifestObject):
	"""
	inspire from:
	https://github.com/buda-base/drs-deposit/blob/2f2d9f7b58977502ae5e90c08e77e7deee4c470b/contrib/tojsondimensions.py#L68

	in short: 
	   - make a compressed json string (no space)
       - gzip it
       - upload on s3 with the right metadata:
          - ContentType='application/json'
          - ContentEncoding='gzip'
          - key: s3folderPrefix+"dimensions.json" (making sure there is a /)
	"""
	pass

def getS3FolderPrefix(workRID, imageGroupID):
	"""
	gives the s3 prefix (~folder) in which the volume will be present.
	inpire from https://github.com/buda-base/buda-iiif-presentation/blob/master/src/main/java/io/bdrc/iiif/presentation/ImageInfoListService.java#L73
	Example:
	   - workRID=W22084, imageGroupID=I0886
	   - result = "Works/60/W22084/images/W22084-0886/
	where:
	   - 60 is the first two characters of the md5 of the string W22084
	   - 0886 is:
	      * the image group ID without the initial "I" if the image group ID is in the form I\d\d\d\d
	      * or else the full image group ID (incuding the "I")
	"""
	pass

def manifestExists(s3folderPrefix):
	"""
	make sure s3folderPrefix+"/dimensions.json" doesn't exist in S3
	"""
	pass

def expandImageList(imageListString):
	"""
	expands an image list string into an array. Image lists are documented on http://purl.bdrc.io/ontology/core/imageList
	see also this example in Java (although probably a bit too sophisticated):
	https://github.com/buda-base/buda-iiif-presentation/blob/d64a2c47c056bfa8658c06c1cddd2566ff4a0a2a/src/main/java/io/bdrc/iiif/presentation/models/ImageListIterator.java
	Example:
	   - imageListString="I2PD44320001.tif:2|I2PD44320003.jpg"
	   - result ["I2PD44320001.tif","I2PD44320002.tif","I2PD44320003.jpg"]
	"""
	pass

def generateManifest(s3folderPrefix, imageList):
	"""
	this actually generates the manifest. See example in the repo. The example corresponds to W22084, image group I0886.
	"""
	res = []
	for imageFileName in imageList:
		s3imageKey = s3folderPrefix+imageFileName
		blob = gets3blob(s3imageKey)
		dimensions = dimensionsFromBlobImage(blob)
		# add filename and dimensions to res
	pass

def dimensionsFromBlobImage(blob):
	"""
	this function returns a dict containing the heigth and width of the image
	the image is the binary blob returned by s3, an image library should be used to treat it
	please do not use the file system (saving as a file and then having the library read it)
	"""

def getVolumeInfos(workRID):
	"""
	this uses the LDS-PDI capabilities to get the volume list of a work, including, for each volume:
	- image list
	- image group ID

	The information should be fetched (in csv or json) from lds-pdi, query for W22084 for instance is:
	http://purl.bdrc.io/query/Work_ImgList?R_RES=bdr:W22084&format=csv&profile=simple&pageSize=500
	"""
	pass