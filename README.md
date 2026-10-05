# Industrial AMR

An autonomous mobile robot (AMR) for industrial environments . The robot navigates a mapped factory area, avoids obstacles that a 2D LiDAR cannot see, docks at a charging station using an AprilTag, and exchanges products with an ABB industrial robot arm.

The project is made of five parts:

1. **Control**: ESP32 low-level motor control, encoders, IMU and safety watchdog
2. **Mapping & Localization**: odometry, sensor fusion (EKF), SLAM, AMCL and Nav2
3. **Perception & Computer Vision**: depth-camera obstacle detection, AprilTag detection and an independent safety monitor
4. **Charging & Docking Station**: battery monitoring, AprilTag-guided docking and automatic charging
5. **ABB Arm Integration**: communication between the AMR and ABB ARM 


## Hardware

| Component | Role |
|---|---|
| Jetson Nano | Main compute: ROS , Nav, SLAM, vision,|
| ESP32 | Low-level control: encoders, per-wheel PID, watchdog |
| RPLIDAR A1 | 2D scan for SLAM, localization and obstacle avoidance |
| Intel RealSense D455 | 3D obstacles and AprilTag detection |
| IMU | Orientation and angular velocity for sensor fusion |
| Wheel encoders | Wheel speed feedback and odometry |
| Battery, BMS and power electronics | Battery with protection, fuse, 5 V and 12 V converters, motor drivers, hardware E-stop |
| Charging station | Charging contacts and an AprilTag marker |
| ABB industrial arm | Loads and unloads products |


## System Overview

```
Nav2 --/cmd_vel--> Control (ESP32) --/wheel_odom, /imu/data--> Localization (EKF)
                                                                    |
RPLIDAR --/scan--> SLAM / AMCL / Safety monitor                     v
                                          /odom + TF map->odom->base_link --> Nav2

D455 --> Perception --/camera/points--> Nav2 costmap
                    --/tag_pose--> Docking manager --/cmd_vel (visual servoing)

Battery monitor --/battery_state--> Docking manager --goal--> Nav2
Safety monitor --/emergency_stop--> Control

```

## Charging and Docking Station

The robot charges itself automatically. An AprilTag on the station lets it align precisely, and the D455 camera reads the tag.

**Station:** charging contacts, an AprilTag mounted at a known height and position, and a known pose in the saved map. 

**Docking sequence:**

| Step | What happens |
|---|---|
| 1. Monitor | The battery monitor publishes the battery level on `/battery_state` |
| 2. Decide | When the level drops below the low threshold (**TODO: set value**), the robot declines new tasks |
| 3. Approach | The docking manager sends a Nav2 goal to a point in front of the station |
| 4. Detect | `apriltag_ros` detects the tag and publishes its pose in the robot frame on `/tag_pose` |
| 5. Align | Visual servoing corrects lateral error, distance and yaw, and publishes `/cmd_vel` |
| 6. Dock | The robot stops at the charging contact point and confirms that charging has started |
| 7. Resume | When the battery is full (**TODO: set value**), the robot undocks and accepts tasks again |

If the tag is lost or alignment fails, the robot backs away and retries (retry limit: **TODO**).

## Team

| Name | Responsibility |
|---|---|
| TODO | TODO |
| TODO | TODO |
| TODO | TODO |



## Repository Layout

The repository has three sections, one for each system.

```
industrial-amr/
├── control/                     # CONTROL
│   ├── esp32_firmware/          # ESP32 firmware: encoders, PID, IMU, watchdog
│   └── amr_control/             # ROS 2 package: Jetson side of the ESP32 link
│
├── mapping_localization/        # MAPPING & LOCALIZATION
│   ├── amr_localization/        # ROS 2 package: wheel odometry, calibration, EKF
│   └── amr_navigation/          # ROS 2 package: slam_toolbox, AMCL, Nav2, maps
│
└── perception_cv/               # PERCEPTION & COMPUTER VISION
    ├── amr_perception/          # ROS 2 package: D455, depth filtering, AprilTag
    └── amr_safety/              # ROS 2 package: independent LiDAR safety monitor
```

`colcon build` finds the ROS 2 packages inside these folders automatically.
