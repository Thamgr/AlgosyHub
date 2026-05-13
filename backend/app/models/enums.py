import enum


class UserRole(str, enum.Enum):
    student = "student"
    teacher = "teacher"


class ContestStatus(str, enum.Enum):
    draft = "draft"
    running = "running"
    finished = "finished"


class ExternalSource(str, enum.Enum):
    codeforces = "codeforces"
    informatics = "informatics"
    leetcode = "leetcode"


class SubmissionVerdict(str, enum.Enum):
    pending = "pending"
    running = "running"
    accepted = "accepted"
    wrong_answer = "wrong_answer"
    time_limit = "time_limit"
    memory_limit = "memory_limit"
    runtime_error = "runtime_error"
    compilation_error = "compilation_error"
    rejected = "rejected"
