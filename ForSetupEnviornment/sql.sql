-- Create and use database
CREATE DATABASE gumawilson;
USE gumawilson;


-- Create summoners table and trigger
CREATE TABLE `gumawilson`.`summoners` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `summoner_name` VARCHAR(100) NOT NULL,
  `summoner_id` VARCHAR(100) NOT NULL,
  `puuid` VARCHAR(100) NOT NULL,
  `created_on` DATETIME NOT NULL DEFAULT NOW(),
  `last_update` DATETIME NOT NULL DEFAULT NOW(),
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
  UNIQUE INDEX `summoner_name_UNIQUE` (`summoner_name` ASC) VISIBLE,
  UNIQUE INDEX `summoner_id_UNIQUE` (`summoner_id` ASC) VISIBLE,
  UNIQUE INDEX `puuid_UNIQUE` (`puuid` ASC) VISIBLE)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;
DROP TRIGGER IF EXISTS `gumawilson`.`summoners_AFTER_UPDATE`;

DELIMITER $$
USE `gumawilson`$$
CREATE DEFINER = CURRENT_USER TRIGGER `gumawilson`.`summoners_AFTER_UPDATE` AFTER UPDATE ON `summoners` FOR EACH ROW
BEGIN
	UPDATE summoners SET last_update = NOW() WHERE id = NEW.id;
END$$
DELIMITER ;

-- Create matches table
CREATE TABLE `gumawilson`.`matches` (
  `id` int NOT NULL AUTO_INCREMENT,
  `match_id` varchar(45) NOT NULL,
  `region_v5` varchar(45) NOT NULL,
  `gameStartTimestamp` bigint NOT NULL,
  `gameMode` varchar(45) NOT NULL,
  `gameType` varchar(45) NOT NULL,
  `gameDuration` int NOT NULL,
  `gameEndTimestamp` bigint NOT NULL,
  `gameEndedInEarlySurrender` tinyint NOT NULL,
  `queueId` int NOT NULL,
  `platformId` varchar(45) NOT NULL,
  `game_end_datetime` datetime(3) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
  UNIQUE INDEX `match_id_UNIQUE` (`match_id` ASC) VISIBLE)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- Create match_players table
CREATE TABLE `gumawilson`.`match_players` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `puuid` VARCHAR(100) NOT NULL,
  `match_id` VARCHAR(45) NOT NULL,
  `kills` INT NOT NULL,
  `deaths` INT NOT NULL,
  `assists` INT NOT NULL,
  `champion_name` VARCHAR(100) NOT NULL,
  `gold_earned` INT NOT NULL,
  `individual_posistion` VARCHAR(45) NOT NULL,
  `damage_to_champions` INT NOT NULL,
  `minions_killed` INT NOT NULL,
  `win` TINYINT NOT NULL DEFAULT 0,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
  INDEX `match_id_idx` (`match_id` ASC) INVISIBLE,
  CONSTRAINT `match_id`
    FOREIGN KEY (`match_id`)
    REFERENCES `gumawilson`.`matches` (`match_id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB
DEFAULT CHARACTER SET = utf8;

-- Storec procedures
USE `gumawilson`;
DROP procedure IF EXISTS `sp_add_new_summoner`;

DELIMITER $$
USE `gumawilson`$$
CREATE PROCEDURE `sp_add_new_summoner` (
  IN p_summoner_name VARCHAR(100),
  IN p_summoner_id VARCHAR(100),
  IN p_puuid VARCHAR(100)
)
BEGIN
  INSERT INTO summoners (summoner_name, summoner_id, puuid)
  VALUES (p_summoner_name, p_summoner_id, p_puuid);
END$$

DELIMITER ;

USE `gumawilson`;
DROP procedure IF EXISTS `sp_summoner_exists`;

DELIMITER $$
USE `gumawilson`$$
CREATE PROCEDURE `sp_summoner_exists` (
  IN p_puuid VARCHAR(100),
  OUT user_exists BOOLEAN
)
BEGIN
  SELECT COUNT(*) INTO user_exists FROM summoners WHERE puuid = p_puuid;
END$$

DELIMITER ;

USE `gumawilson`;
DROP procedure IF EXISTS `sp_match_exists`;

DELIMITER $$
USE `gumawilson`$$
CREATE PROCEDURE `sp_match_exists` (
  IN p_match_id VARCHAR(45),
  OUT match_exists BOOLEAN
)
BEGIN
  SELECT COUNT(*) INTO match_exists FROM matches WHERE match_id = p_match_id;
END$$

DELIMITER ;

USE `gumawilson`;
DROP procedure IF EXISTS `sp_add_new_match`;

DELIMITER $$
USE `gumawilson`$$
CREATE PROCEDURE `sp_add_new_match` (
  IN p_match_id VARCHAR(45),
  IN p_region_v5 VARCHAR(45),
  IN p_gameStartTimestamp BIGINT,
  IN p_gameMode VARCHAR(45),
  IN p_gameType VARCHAR(45),
  IN p_gameDuration INT,
  IN p_gameEndTimestamp BIGINT,
  IN p_gameEndedInEarlySurrender BOOLEAN,
  IN p_queueId INT,
  IN p_platformId VARCHAR(45),
  IN p_game_end_datetime DATETIME(3)
)
BEGIN
  IF NOT EXISTS (SELECT * FROM matches WHERE match_id = p_match_id)
  THEN
    INSERT INTO matches (match_id, region_v5, gameStartTimestamp, gameMode, gameType, gameDuration, gameEndTimestamp, gameEndedInEarlySurrender, queueId, platformId, game_end_datetime)
    VALUES (p_match_id, p_region_v5, p_gameStartTimestamp, p_gameMode, p_gameType, p_gameDuration, p_gameEndTimestamp, p_gameEndedInEarlySurrender, p_queueId, p_platformId,p_game_end_datetime);
  END IF;
END$$

DELIMITER ;

USE `gumawilson`;
DROP procedure IF EXISTS `sp_add_new_match_players_record`;

DELIMITER $$
USE `gumawilson`$$
CREATE PROCEDURE `sp_add_new_match_players_record` (
  IN p_puuid VARCHAR(100),
  IN p_match_id VARCHAR(45),
  IN p_kills INT,
  IN p_deaths INT,
  IN p_assists INT,
  IN p_champion_name VARCHAR(100),
  IN p_gold_earned INT,
  IN p_individual_posistion VARCHAR(45),
  IN p_damage_to_champions INT,
  IN p_minions_killed INT,
  IN p_win BOOLEAN
)
BEGIN
  IF NOT EXISTS (SELECT * FROM match_players WHERE match_id = p_match_id AND puuid = p_puuid)
  THEN
    INSERT INTO match_players (puuid, match_id, kills, deaths, assists, champion_name, gold_earned, individual_posistion, damage_to_champions, minions_killed, win)
    VALUES (p_puuid, p_match_id, p_kills, p_deaths, p_assists, p_champion_name, p_gold_earned, p_individual_posistion, p_damage_to_champions, p_minions_killed, p_win);
  END IF;
END$$

DELIMITER ;

USE `gumawilson`;
DROP procedure IF EXISTS `sp_check_is_win`;

DELIMITER $$
USE `gumawilson`$$
CREATE PROCEDURE `sp_check_is_win` (
  IN p_match_id VARCHAR(45),
  IN p_puuid  VARCHAR(100),
  OUT p_win INT
)
BEGIN
  SELECT IFNULL(match_players.win, -1) INTO p_win FROM match_players
  INNER JOIN matches
  ON  match_players.puuid = p_puuid 
  AND match_players.match_id = p_match_id
  AND matches.match_id = p_match_id
  AND matches.gameDuration > 210;
END$$

DELIMITER ;

