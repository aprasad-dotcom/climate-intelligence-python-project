"""Small executable supporting exercises retained from PAL Experiments 01 and 03.

These student-mark examples are independent of Climate Intelligence's domain logic;
they preserve the separate getter/setter and multilevel-inheritance exercises.
"""


class StudentMarks:
    """Experiment 01: encapsulated marks with getter and setter methods."""

    def __init__(self, roll_number, name, marks):
        self.roll_number = str(roll_number).strip()
        self.name = " ".join(str(name).split()).title()
        self.__marks = []
        self.set_marks(marks)

    def set_marks(self, marks):
        values = [float(mark) for mark in marks]
        if len(values) != 4 or any(mark < 0 or mark > 100 for mark in values):
            raise ValueError("Exactly four subject marks between 0 and 100 are required.")
        self.__marks = values

    def get_marks(self):
        return tuple(self.__marks)

    def total(self):
        return sum(self.__marks)

    def percentage(self):
        return self.total() / 4


class AcademicMarks:
    """Experiment 03: parent record for roll/name and three subject marks."""

    def __init__(self, roll_number, name, marks):
        self.roll_number = str(roll_number).strip()
        self.name = " ".join(str(name).split()).title()
        self.marks = [float(mark) for mark in marks]
        if len(self.marks) != 3 or any(mark < 0 or mark > 100 for mark in self.marks):
            raise ValueError("Exactly three subject marks between 0 and 100 are required.")


class SportsStudentMarks(AcademicMarks):
    """Experiment 03: child adds the sports mark using the parent constructor."""

    def __init__(self, roll_number, name, marks, sports_mark):
        super().__init__(roll_number, name, marks)
        self.sports_mark = float(sports_mark)
        if not 0 <= self.sports_mark <= 100:
            raise ValueError("Sports mark must be between 0 and 100.")


class FinalStudentResult(SportsStudentMarks):
    """Experiment 03: derived result using inherited academic and sports data."""

    def total_all(self):
        return sum(self.marks) + self.sports_mark

    def average_all(self):
        return self.total_all() / 4

    def report(self):
        return {"roll_number": self.roll_number, "name": self.name,
                "marks": tuple(self.marks), "sports_mark": self.sports_mark,
                "total": self.total_all(), "average": self.average_all()}
