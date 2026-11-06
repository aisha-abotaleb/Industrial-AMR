import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    pkg = get_package_share_directory('articubot_docking')
    models = os.path.join(pkg, 'models')
    old = os.environ.get('GAZEBO_MODEL_PATH', '')

    # Gazebo Classic must be able to resolve model://apriltag_dock
    set_model_path = SetEnvironmentVariable(
        'GAZEBO_MODEL_PATH', models + (os.pathsep + old if old else ''))

    # Re-use articubot_one's own simulation launch, only swapping the world.
    sim = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('articubot_one'), 'launch', 'launch_sim.launch.py')),
        launch_arguments={'world': LaunchConfiguration('world')}.items())

    world_arg = DeclareLaunchArgument(
        'world', default_value=os.path.join(pkg, 'worlds', 'cafe.world'))

    return LaunchDescription([world_arg, set_model_path, sim])
