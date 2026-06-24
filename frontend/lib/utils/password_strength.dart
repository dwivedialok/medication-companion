enum PasswordStrength { empty, weak, fair, good, strong }

PasswordStrength evaluatePasswordStrength(String password) {
  if (password.isEmpty) return PasswordStrength.empty;

  var score = 0;
  if (password.length >= 6) score++;
  if (password.length >= 8) score++;
  if (password.length >= 12) score++;
  if (RegExp(r'[A-Z]').hasMatch(password)) score++;
  if (RegExp(r'[a-z]').hasMatch(password)) score++;
  if (RegExp(r'[0-9]').hasMatch(password)) score++;
  if (RegExp(r'[!@#$%^&*(),.?":{}|<>\[\]\\/_+=\-~`]').hasMatch(password)) {
    score++;
  }

  if (password.length < 6) return PasswordStrength.weak;
  if (score <= 3) return PasswordStrength.weak;
  if (score <= 4) return PasswordStrength.fair;
  if (score <= 5) return PasswordStrength.good;
  return PasswordStrength.strong;
}
