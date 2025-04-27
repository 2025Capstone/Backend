INSERT INTO instructor (name, email, password) VALUES
                                                   ('노서영', 'seoyoung.no@example.com', '$2b$12$XDT1Ro5z9v3F76SO2HcfT.XzDGR3geJ7x3HIgDrBqOyNwFbAJB2p.'),
                                                   ('이의종', 'uijong.lee@example.com', '$2b$12$XDT1Ro5z9v3F76SO2HcfT.XzDGR3geJ7x3HIgDrBqOyNwFbAJB2p.'),
                                                   ('조희승', 'heeseung.jo@example.com', '$2b$12$XDT1Ro5z9v3F76SO2HcfT.XzDGR3geJ7x3HIgDrBqOyNwFbAJB2p.');



INSERT INTO lecture (instructor_id, name) VALUES
                                              (1, '자료구조'),
                                              (1, '데이터베이스'),
                                              (2, '자료구조'),
                                              (3, '컴퓨터구조'),
                                              (3, '운영체제');