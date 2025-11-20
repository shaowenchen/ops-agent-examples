docker build -t ${REGISTRY}/ops-agent:slo -f Dockerfile . --push
echo "--------------------------------"
echo "build and push image: $REGISTRY/ops-agent:slo"
echo "--------------------------------"