

FROM redhat/ubi10-minimal:10.1@sha256:a74a7a92d3069bfac09c6882087771fc7db59fa9d8e16f14f4e012fe7288554c

ARG TARGETPLATFORM
ARG BUILDPLATFORM

RUN microdnf -y install \
  python3 \
  python3-pip && \
  microdnf clean all

WORKDIR /usr/local/src/kfp/components

RUN --mount=type=bind,source=requirements.txt,target=/root/requirements.txt,relabel=shared pip install -r /root/requirements.txt

COPY src/* ./
COPY component_metadata/* ./component_metadata/*

RUN cat <<EOF > kfp_config.ini 
[Components]
read_data = read_data_component.py
search_space_preparation = search_space_preparation_component.py
rag_templates_optimization = rag_templates_optimization_component.py
EOF

CMD ["/bin/bash", "-i"]
