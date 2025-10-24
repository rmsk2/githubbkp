# Definitions
img=grap.de/githubbkp:v1
binary=githubbkp.tar

# cleanup
rm $binary

# create image via Dockerfile
buildah build -t $img
buildah push $img oci-archive:$binary:$img
buildah rmi $img

# Distribute image
scp $binary martin@debasus:$binary
scp $binary martin@debasus2:$binary
#scp $binary martin@debshuttle:$binary

