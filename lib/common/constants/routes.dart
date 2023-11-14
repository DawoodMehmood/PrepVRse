import 'package:get/get.dart';
import 'package:prepvrse/screens/login/ui_login_screen.dart';
import 'package:prepvrse/screens/signup/ui_signup_screen.dart';

appRoutes() => [
      GetPage(
        name: '/signup',
        page: () => const SignUpScreen(),
        transition: Transition.fadeIn,
        transitionDuration: const Duration(milliseconds: 200),
      ),
      GetPage(
        name: '/login',
        page: () => const LoginScreen(),
        transition: Transition.fadeIn,
        transitionDuration: const Duration(milliseconds: 200),
      ),
    ];
