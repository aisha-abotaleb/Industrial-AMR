#!/usr/bin/env python3
"""
Tiny CLI client for the Nav2 docking server (Humble: opennav_docking_msgs).

  ros2 run articubot_docking dock_client.py dock   --dock-id dock0
  ros2 run articubot_docking dock_client.py dock   --dock-id dock0 --navigate   # needs Nav2 navigate_to_pose
  ros2 run articubot_docking dock_client.py undock --dock-type articubot_dock
"""
import argparse
import sys

import rclpy
from rclpy.action import ActionClient
from rclpy.node import Node

from opennav_docking_msgs.action import DockRobot, UndockRobot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('command', choices=['dock', 'undock'])
    ap.add_argument('--dock-id', default='dock0')
    ap.add_argument('--dock-type', default='articubot_dock')
    ap.add_argument('--navigate', action='store_true',
                    help='let the docking server drive to the staging pose using Nav2 first')
    args = ap.parse_args()

    rclpy.init()
    node = Node('dock_client')

    if args.command == 'dock':
        client = ActionClient(node, DockRobot, 'dock_robot')
        goal = DockRobot.Goal()
        goal.use_dock_id = True
        goal.dock_id = args.dock_id
        goal.navigate_to_staging_pose = bool(args.navigate)
        goal.max_staging_time = 1000.0
    else:
        client = ActionClient(node, UndockRobot, 'undock_robot')
        goal = UndockRobot.Goal()
        goal.dock_type = args.dock_type
        goal.max_undocking_time = 30.0

    if not client.wait_for_server(timeout_sec=10.0):
        node.get_logger().error('Action server not available (is docking_server active?)')
        sys.exit(1)

    def feedback(fb):
        node.get_logger().info(str(fb.feedback), throttle_duration_sec=1.0)

    send = client.send_goal_async(goal, feedback_callback=feedback)
    rclpy.spin_until_future_complete(node, send)
    handle = send.result()
    if not handle.accepted:
        node.get_logger().error('Goal rejected')
        sys.exit(1)

    res_future = handle.get_result_async()
    rclpy.spin_until_future_complete(node, res_future)
    result = res_future.result().result
    node.get_logger().info(f'success={result.success} error_code={result.error_code}')
    node.destroy_node()
    rclpy.shutdown()
    sys.exit(0 if result.success else 2)


if __name__ == '__main__':
    main()
