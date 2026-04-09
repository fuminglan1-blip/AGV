cmake_minimum_required(VERSION 3.5)

project(ros_gz_example_bringup)

find_package(ament_cmake REQUIRED)
find_package(ros_gz_example_description REQUIRED)
find_package(ros_gz_example_gazebo REQUIRED)

# Install project launch files
install(
  DIRECTORY
    launch/
  DESTINATION share/${PROJECT_NAME}/launch
)

# Install project configuration files
install(
  DIRECTORY
    config/
  DESTINATION share/${PROJECT_NAME}/config
)

# Install the RViz helper nodes with the bringup package so the default launch
# chain runs entirely from the built overlay instead of mixing install/share
# launch files with source-tree Python scripts.
install(
  PROGRAMS
    ${CMAKE_CURRENT_SOURCE_DIR}/../../web_dashboard/odom_tf_publisher.py
    ${CMAKE_CURRENT_SOURCE_DIR}/../../web_dashboard/odom_visual_helper.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
