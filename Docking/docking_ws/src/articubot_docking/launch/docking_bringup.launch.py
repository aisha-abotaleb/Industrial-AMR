import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    pkg = get_package_share_directory('articubot_docking')
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_rectify = LaunchConfiguration('use_rectify')

    def include(name, args):
        return IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', name)),
            launch_arguments=args.items())

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('use_rectify', default_value='false'),
        include('apriltag_dock.launch.py',
                {'use_sim_time': use_sim_time, 'use_rectify': use_rectify}),
        include('docking_server.launch.py', {'use_sim_time': use_sim_time}),
    ])
