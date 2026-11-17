-- MySQL 8 actual DDL; generated after acceptance, seed counters removed.
CREATE TABLE `audits` (
  `id` int NOT NULL AUTO_INCREMENT,
  `actor` varchar(100) DEFAULT NULL,
  `action` varchar(200) DEFAULT NULL,
  `created` varchar(40) DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `cohorts` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) DEFAULT NULL,
  `start_week` varchar(10) DEFAULT NULL,
  `end_week` varchar(10) DEFAULT NULL,
  `as_of` varchar(10) DEFAULT NULL,
  `horizon` int DEFAULT NULL,
  `state` varchar(20) DEFAULT NULL,
  `result` json DEFAULT NULL,
  `error` text,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `events` (
  `id` int NOT NULL AUTO_INCREMENT,
  `code` varchar(60) NOT NULL,
  `learner` varchar(60) NOT NULL,
  `occurred_at` varchar(40) NOT NULL,
  `course` varchar(40) DEFAULT NULL,
  `note` text,
  PRIMARY KEY (`id`),
  UNIQUE KEY `code` (`code`),
  KEY `ix_events_learner` (`learner`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `email` varchar(100) NOT NULL,
  `password` varchar(200) DEFAULT NULL,
  `role` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `interventions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `cohort_id` int DEFAULT NULL,
  `cohort_week` varchar(10) DEFAULT NULL,
  `week_index` int DEFAULT NULL,
  `note` text,
  `members` json DEFAULT NULL,
  `status` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `cohort_id` (`cohort_id`),
  CONSTRAINT `interventions_ibfk_1` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `releases` (
  `id` int NOT NULL AUTO_INCREMENT,
  `request_id` varchar(64) NOT NULL,
  `cohort_id` int NOT NULL,
  `name` varchar(100) DEFAULT NULL,
  `epsilon` decimal(6,4) NOT NULL,
  `state` varchar(20) DEFAULT 'pending',
  `result` json DEFAULT NULL,
  `error` text,
  `noise_seed` varchar(64) DEFAULT NULL,
  `created_by` varchar(100) DEFAULT NULL,
  `created` varchar(40) DEFAULT NULL,
  `published` varchar(40) DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `request_id` (`request_id`),
  KEY `cohort_id` (`cohort_id`),
  CONSTRAINT `releases_ibfk_1` FOREIGN KEY (`cohort_id`) REFERENCES `cohorts` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE `privacy_budget` (
  `id` int NOT NULL AUTO_INCREMENT,
  `total` decimal(8,4) NOT NULL,
  `spent` decimal(8,4) NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

INSERT INTO `privacy_budget` (`id`, `total`, `spent`) VALUES (1, 1.0000, 0.0000);

