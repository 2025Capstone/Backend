INSERT INTO instructor (name, email, password, is_approved) VALUES
                                                   ('노서영', 'seoyoung.no@example.com', '$2b$12$XDT1Ro5z9v3F76SO2HcfT.XzDGR3geJ7x3HIgDrBqOyNwFbAJB2p.',1),
                                                   ('이의종', 'uijong.lee@example.com', '$2b$12$XDT1Ro5z9v3F76SO2HcfT.XzDGR3geJ7x3HIgDrBqOyNwFbAJB2p.',1),
                                                   ('조희승', 'heeseung.jo@example.com', '$2b$12$XDT1Ro5z9v3F76SO2HcfT.XzDGR3geJ7x3HIgDrBqOyNwFbAJB2p.',1);



INSERT INTO lecture (instructor_id, name, is_public, schedule, classroom) VALUES
                                              (1, '자료구조',1,"금1-3", "A101"),
                                              (1, '운영체제',1,"금4-6", "A102"),
                                              (2, '데이터베이스',1,"화1-3", "A201"),
                                              (2, '컴퓨터구조',1,"화4-6", "A202"),
                                              (3, '소프트웨어공학',1,"수1-3", "A301"),
                                              (3, '인공지능',1,"수4-6", "A302");