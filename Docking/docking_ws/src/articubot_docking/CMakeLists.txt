cmake_minimum_required(VERSION 3.8)
project(articubot_docking)

find_package(ament_cmake REQUIRED)

install(
  PROGRAMS
    scripts/dock_pose_publisher.py
    scripts/dock_client.py
  DESTINATION lib/${PROJECT_NAME}
)

install(
  DIRECTORY config launch models worlds
  DESTINATION share/${PROJECT_NAME}
)

ament_package()
