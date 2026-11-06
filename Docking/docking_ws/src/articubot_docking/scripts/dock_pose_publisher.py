#!/usr/bin/env python3
"""
Turns the AprilTag TF (published by apriltag_ros) into the geometry_msgs/PoseStamped on
`detected_dock_pose` that Nav2's SimpleChargingDock plugin (opennav_docking) listens to.

Published pose (in `fixed_frame`, normally odom):
  * position  = centre of the tag
  * yaw       = direction pointing INTO the dock/wall (= robot heading when docked)
  * z = 0, roll = pitch = 0   (diff-drive robot only cares about x, y, yaw)

Because heading is already "into the wall", docking_server.yaml uses zero external rotations
and only external_detection_translation_x to say how far in front of the tag base_link stops.

Assumes apriltag_ros runs with z_up: false  (tag z axis points into the tag).
"""
import math

import rclpy
from geometry_msgs.msg import PoseStamped
from rclpy.node import Node
from rclpy.time import Time
from tf2_ros import Buffer, TransformException, TransformListener


def tag_z_axis(qx, qy, qz, qw):
    """Tag +Z axis expressed in the parent frame (3rd column of the rotation matrix)."""
    return (
        2.0 * (qx * qz + qw * qy),
        2.0 * (qy * qz - qw * qx),
        1.0 - 2.0 * (qx * qx + qy * qy),
    )


def dock_pose_from_tag(tx, ty, quat_xyzw, z_into_wall=True):
    """Return (x, y, yaw) of the dock pose, or None if the tag normal is (almost) vertical."""
    zx, zy, _ = tag_z_axis(*quat_xyzw)
    if not z_into_wall:
        zx, zy = -zx, -zy
    if math.hypot(zx, zy) < 0.2:   # tag lying flat -> no usable horizontal heading
        return None
    return tx, ty, math.atan2(zy, zx)


class DockPosePublisher(Node):
    def __init__(self):
        super().__init__('dock_pose_publisher')
        self.declare_parameter('fixed_frame', 'odom')
        self.declare_parameter('tag_frame', 'dock_tag')
        self.declare_parameter('output_topic', 'detected_dock_pose')
        self.declare_parameter('rate', 20.0)
        self.declare_parameter('max_age', 0.5)             # seconds; ignore older detections
        self.declare_parameter('tag_z_points_into_wall', True)

        self.fixed_frame = self.get_parameter('fixed_frame').value
        self.tag_frame = self.get_parameter('tag_frame').value
        self.max_age = float(self.get_parameter('max_age').value)
        self.z_into_wall = bool(self.get_parameter('tag_z_points_into_wall').value)

        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.pub = self.create_publisher(
            PoseStamped, self.get_parameter('output_topic').value, 10)
        self.last_stamp = None
        self.create_timer(1.0 / float(self.get_parameter('rate').value), self.tick)
        self.get_logger().info(
            f'Waiting for TF {self.fixed_frame} -> {self.tag_frame} ...')

    def tick(self):
        try:
            tf = self.tf_buffer.lookup_transform(self.fixed_frame, self.tag_frame, Time())
        except TransformException:
            return                                          # tag not seen (yet / any more)

        stamp = Time.from_msg(tf.header.stamp)
        if self.last_stamp is not None and stamp == self.last_stamp:
            return                                          # same detection as before
        if (self.get_clock().now() - stamp).nanoseconds * 1e-9 > self.max_age:
            return                                          # stale detection
        self.last_stamp = stamp

        t, q = tf.transform.translation, tf.transform.rotation
        res = dock_pose_from_tag(t.x, t.y, (q.x, q.y, q.z, q.w), self.z_into_wall)
        if res is None:
            self.get_logger().warn('Tag normal is vertical - check z_up / tag orientation',
                                   throttle_duration_sec=2.0)
            return
        x, y, yaw = res

        msg = PoseStamped()
        msg.header.stamp = tf.header.stamp                  # keep ORIGINAL stamp (plugin checks its age)
        msg.header.frame_id = self.fixed_frame
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.orientation.z = math.sin(yaw / 2.0)
        msg.pose.orientation.w = math.cos(yaw / 2.0)
        self.pub.publish(msg)


def main():
    rclpy.init()
    node = DockPosePublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()


if __name__ == '__main__':
    main()
