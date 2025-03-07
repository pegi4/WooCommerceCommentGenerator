<?php
/**
 * Handles Comment Post to WordPress with disabled comment checking for temporary testing.
 *
 * @package WordPress
 */

if ('POST' !== $_SERVER['REQUEST_METHOD']) {
    $protocol = $_SERVER['SERVER_PROTOCOL'];
    if (!in_array($protocol, array('HTTP/1.1', 'HTTP/2', 'HTTP/2.0', 'HTTP/3'), true)) {
        $protocol = 'HTTP/1.0';
    }

    header('Allow: POST');
    header("$protocol 405 Method Not Allowed");
    header('Content-Type: text/plain');
    exit;
}

/** Sets up the WordPress Environment. */
require __DIR__ . '/wp-load.php';

nocache_headers();

// Ročno vstavi komentar brez preverjanja
$comment_data = array(
    'comment_post_ID'      => (int) $_POST['comment_post_ID'],
    'comment_author'       => wp_unslash($_POST['author']),
    'comment_author_email' => wp_unslash($_POST['email']),
    'comment_content'      => wp_unslash($_POST['comment']),
    'comment_type'         => 'comment',
    'comment_parent'       => isset($_POST['comment_parent']) ? absint($_POST['comment_parent']) : 0,
    'user_id'              => 0, // 0 za neprijavljene uporabnike
    'comment_date'         => current_time('mysql'),
    'comment_date_gmt'     => current_time('mysql', 1),
    'comment_approved'     => 1, // Takoj odobren brez moderiranja
);

// Vstavi komentar v bazo
$comment_id = wp_insert_comment($comment_data);

if ($comment_id) {
    // Shrani oceno, če je poslana prek obrazca
    if (isset($_POST['rating']) && is_numeric($_POST['rating'])) {
        update_comment_meta($comment_id, 'rating', intval($_POST['rating']));
    }

    $comment = get_comment($comment_id); // Pridobi objekt komentarja
    $user = wp_get_current_user();
    $cookies_consent = isset($_POST['wp-comment-cookies-consent']);

    /**
     * Fires after comment cookies are set.
     *
     * @since 3.4.0
     * @since 4.9.6 The `$cookies_consent` parameter was added.
     *
     * @param WP_Comment $comment         Comment object.
     * @param WP_User    $user            Comment author's user object. The user may not exist.
     * @param bool       $cookies_consent Comment author's consent to store cookies.
     */
    do_action('set_comment_cookies', $comment, $user, $cookies_consent);

    // Določi lokacijo za preusmeritev
    $location = empty($_POST['redirect_to']) ? get_comment_link($comment) : $_POST['redirect_to'] . '#comment-' . $comment->comment_ID;

    /**
     * Filters the location URI to send the commenter after posting.
     *
     * @since 2.0.5
     *
     * @param string     $location The 'redirect_to' URI sent via $_POST.
     * @param WP_Comment $comment  Comment object.
     */
    $location = apply_filters('comment_post_redirect', $location, $comment);

    wp_safe_redirect($location);
    exit;
} else {
    wp_die(
        '<p>Napaka pri oddaji komentarja.</p>',
        __('Comment Submission Failure'),
        array(
            'response'  => 500,
            'back_link' => true,
        )
    );
}