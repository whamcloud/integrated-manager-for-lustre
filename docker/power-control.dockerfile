FROM imlteam/python-service-base:6.3.0

RUN yum install -y epel-release \
  && yum clean all \
  && yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/managerforlustre/manager-for-lustre-devel/repo/epel-7/managerforlustre-manager-for-lustre-devel-epel-7.repo \
  && yum clean all \
  && yum install -y python-pip \
  && pip uninstall -y urllib3 \
  && yum autoremove -y python-pip \
  && rm -rf /root/.cache/pip \
  && yum install -y fence-agents-all fence-agents-vbox \
  && rm -f /etc/yum.repos.d/managerforlustre-manager-for-lustre-devel-epel-7.repo \
  && yum clean all

CMD ["python", "./manage.py", "chroma_service", "--name=power_control", "power_control", "--console"]
