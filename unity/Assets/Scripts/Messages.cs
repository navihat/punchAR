using System;

// Message format = contract with Python (docs/PROJECT_OVERVIEW.md §5). Do not change alone.
// Parse with JsonUtility.FromJson<...>(json) after checking "type".

[Serializable]
public class BaseMessage { public string type; public long t; }

[Serializable]
public class HandPose { public string hand; public float x; public float y; public string shape; }

[Serializable]
public class PoseMessage { public string type; public long t; public HandPose[] hands; }

[Serializable]
public class StrikeMessage { public string type; public long t; public string hand; public string kind; public float x; public float y; }

[Serializable]
public class HandLostMessage { public string type; public long t; public string hand; }
