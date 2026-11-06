import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch_ros.actions import ComposableNodeContainer, Node
from launch_ros.descriptions import ComposableNode


def generate_launch_description():
    pkg = get_package_share_directory('articubot_docking')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rectify = LaunchConfiguration('use_rectify')

    # Gazebo's camera has no lens distortion -> raw == rectified, so rectify is only for the real camera.
    image_topic = PythonExpression(
        ["'/camera/image_rect' if '", use_rectify, "' == 'true' else '/camera/image_raw'"])

    rectify = ComposableNodeContainer(
        name='rectify_container',
        namespace='',
        package='rclcpp_components',
        executable='component_container',
        condition=IfCondition(use_rectify),
        composable_node_descriptions=[
            ComposableNode(
                package='image_proc',
                plugin='image_proc::RectifyNode',
                name='rectify_node',
                remappings=[('image', '/camera/image_raw'),
                            ('camera_info', '/camera/camera_info'),
                            ('image_rect', '/camera/image_rect')],
                parameters=[{'use_sim_time': use_sim_time}],
            )
        ],
        output='screen',
    )

    apriltag = Node(
        package='apriltag_ros',
        executable='apriltag_node',
        name='apriltag',
        output='screen',
        remappings=[('image_rect', image_topic),
                    ('camera_info', '/camera/camera_info')],
        parameters=[os.path.join(pkg, 'config', 'apriltag_36h11.yaml'),
                    {'use_sim_time': use_sim_time}],
    )

    dock_pose_publisher = Node(
        package='articubot_docking',
        executable='dock_pose_publisher.py',
        name='dock_pose_publisher',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time,
                     'fixed_frame': 'odom',
                     'tag_frame': 'dock_tag',
                     'tag_z_points_into_wall': False}],
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('use_rectify', default_value='false',
                              description='true on the real robot with a calibrated camera'),
        rectify,
        apriltag,
        dock_pose_publisher,
    ])
