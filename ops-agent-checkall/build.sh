docker build -t ${REGISTRY}/ops-agent:checkall -f Dockerfile . --push
echo "--------------------------------"
echo "build and push image: $REGISTRY/ops-agent:checkall"
echo "--------------------------------"