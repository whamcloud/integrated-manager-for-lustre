FROM imlteam/manager-service-base:extract-nginx

CMD ["python", "./manage.py", "chroma_service", "--name=power_control", "power_control", "--console"]