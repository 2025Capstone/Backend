INSERT INTO instructor (name, email, password) VALUES
                                                   ('노서영', 'seoyoung.no@example.com', 'password123!'),
                                                   ('이의종', 'uijong.lee@example.com', 'securepass456!'),
                                                   ('조희승', 'heeseung.jo@example.com', 'mypass789!');

INSERT INTO lecture (instructor_id, name) VALUES
                                              (1, '자료구조'),
                                              (1, '데이터베이스'),
                                              (2, '자료구조'),
                                              (3, '컴퓨터구조'),
                                              (3, '운영체제');