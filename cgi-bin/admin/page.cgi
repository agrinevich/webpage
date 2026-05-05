#!/usr/bin/perl

use strict;
use warnings;

use CGI;
use FindBin qw($Bin);
use Carp    qw(carp croak);
use File::Copy; # copy()
use Config::Tiny;

use lib "$Bin/../lib";
use Printer;
use Utils;

my $log = "$Bin/../logs/page.log";
open( STDERR, '>>', $log ) or croak("Failed to append $log\n");

my $cfile = "$Bin/../main.conf";
my $conf  = Config::Tiny->read($cfile)
    or croak( "Failed to read: $cfile , " . Config::Tiny->errstr . "\n" );

my $SCRIPT   = $ENV{SCRIPT_NAME};
my $SCHEME   = $ENV{REQUEST_SCHEME};
my $HOST     = $ENV{HTTP_HOST};
my $BASE_URL = $SCHEME . '://' . $HOST . $SCRIPT;
my $HTML_DIR = "$Bin/../.." . $conf->{site}->{html_path};

$CGI::POST_MAX = 1024 * 1024 * $conf->{page}->{max_upload_mb};
# $CGI::DISABLE_UPLOADS = 1;

my $q  = CGI->new();
my $do = $q->param('do') // q{};

my $p = Printer->new(
    root_dir => "$Bin/../..",
    tpl_path => '/cgi-bin/tpl',
);

my $page_left = q{};
my $page_main = q{};

if    ( $do eq 'go' )            { ( $page_left, $page_main ) = go($q); }
elsif ( $do eq 'update' )        { update($q); }
elsif ( $do eq 'create-file' )   { create_file($q); }
elsif ( $do eq 'download-file' ) { download_file($q); }
elsif ( $do eq 'upload-file' )   { upload_file($q); }
elsif ( $do eq 'create-dir' )    { create_dir($q); }
elsif ( $do eq 'delete-file' )   { delete_file($q); }
elsif ( $do eq 'delete-dir' )    { delete_dir($q); }
else                             { ( $page_left, $page_main ) = go($q); }

print $q->header(
    -type    => 'text/html',
    -charset => 'utf-8',
);

print $p->do_render(
    tpl_file => 'admin.html',
    escape   => 0,
    vars     => {
        page_left => $page_left,
        page_main => $page_main,
    },
);

close(STDERR);
exit();

sub go {
    my ($q) = @_;

    my $path     = $q->param('p')   // q{}; # relative path to current dir
    my $filename = $q->param('f')   // q{}; # choosen file name (if any)
    my $msg      = $q->param('msg') // q{}; # error message

    my $list    = q{};                      # navi links on left side
    my $details = q{};                      # content at main area

    my $canedit = $conf->{page}->{can_edit};
    my @canedit = split /[,]/, $canedit;
    my %canedit = ();
    foreach my $file_ext (@canedit) {
        $canedit{ lc $file_ext } = 1;
    }

    my @chunks = split( /[.]/, $filename );
    my $ext    = q{};
    if ( scalar @chunks > 1 ) {
        $ext = pop @chunks;
    }
    my $ext_lc = lc $ext;

    if ($filename) {
        if ( !exists $canedit{$ext_lc} ) {
            $details = $p->do_render(
                tpl_file => 'page/take-file.html',
                escape   => 0,
                vars     => {
                    filename => $filename,
                    path     => $path,
                    msg      => $msg,
                },
            );
        }
        else {
            my $file      = sprintf( '%s/%s/%s', $HTML_DIR, $path, $filename );
            my $html_code = Utils::read_file( file => $file );
            $details = $p->do_render(
                tpl_file => 'page/edit-file.html',
                escape   => 0,
                vars     => {
                    filename  => $filename,
                    path      => $path,
                    html_code => $html_code,
                    msg       => $msg,
                },
            );
        }
    }
    else {
        # TODO: report total size of files
        $details = $p->do_render(
            tpl_file => 'page/edit-dir.html',
            escape   => 0,
            vars     => {
                path => $path,
                msg  => $msg,
            },
        );
    }

    my $parent_path = q{};
    my $cur_dir     = $HTML_DIR;
    if ( $path ne q{} ) {
        $cur_dir .= '/' . $path;

        $parent_path = get_parent_path($path);
        $list .= $p->do_render(
            tpl_file => 'page/list-dir.html',
            escape   => 0,
            vars     => {
                name => '/..',
                path => $parent_path,
            },
        );
    }

    my ( $a_dirs, $a_files ) = Utils::read_dir( dir => $cur_dir );

    foreach my $name ( sort @{$a_dirs} ) {
        $list .= $p->do_render(
            tpl_file => 'page/list-dir.html',
            escape   => 0,
            vars     => {
                name => $name,
                path => sprintf( '%s/%s', $path, $name ),
            },
        );
    }

    my $active = q{};
    foreach my $name ( sort @{$a_files} ) {
        if   ( $name eq $filename ) { $active = ' class="active"'; }
        else                        { $active = q{}; }
        $list .= $p->do_render(
            tpl_file => 'page/list-file.html',
            escape   => 0,
            vars     => {
                name   => $name,
                path   => $path,
                active => $active,
            },
        );
    }

    $list .= $p->do_render(
        tpl_file => 'page/list-extra.html',
        escape   => 0,
        vars     => {
            path => $path,
        },
    );

    return ( $list, $details );
}

sub download_file {
    my ($q) = @_;

    my $path     = $q->param('p') // q{};
    my $filename = $q->param('f') // q{};

    my $file = sprintf( '%s/%s/%s', $HTML_DIR, $path, $filename );

    print $q->header(
        -type       => 'application/octet-stream',
        -attachment => $filename,
    );

    binmode STDOUT;

    open( my $fh, '<', $file ) or croak($!);
    print while <$fh>;
    close($fh);

    exit();
}

sub get_parent_path {
    my ($path) = @_;

    my @chunks = split /\//, $path;
    my $num    = scalar(@chunks);
    if ( $num < 2 ) {
        return q{};
    }

    pop(@chunks);
    return join( '/', @chunks );
}

sub update {
    my ($q) = @_;

    my $path     = $q->param('p')         // q{}; # relative path to current dir
    my $filename = $q->param('f')         // q{}; # choosen file name
    my $body     = $q->param('html_code') // q{};

    my $file = sprintf( '%s/%s/%s', $HTML_DIR, $path, $filename );

    my $rc = Utils::write_file(
        file => $file,
        body => $body,
    );

    print $q->redirect( $BASE_URL . "?do=go&p=$path&f=$filename" );
    exit();
}

sub create_file {
    my ($q) = @_;

    my $path     = $q->param('p')    // q{}; # relative path to current dir
    my $filename = $q->param('name') // q{}; # new file name

    if ( !$filename ) {
        print $q->redirect( $BASE_URL . "?do=go&p=$path&msg=filename-required" );
        exit();
    }
    elsif ( $filename =~ /\W/ ) {
        print $q->redirect( $BASE_URL . "?do=go&p=$path&msg=english-letters-and-digits" );
        exit();
    }

    my $file = sprintf( '%s/%s/%s', $HTML_DIR, $path, $filename );
    if ( -f $file ) {
        print $q->redirect( $BASE_URL . "?do=go&p=$path&msg=file-exists" );
        exit();
    }

    my $rc = Utils::write_file(
        file => $file,
        body => 'put content here.',
    );

    print $q->redirect( $BASE_URL . "?do=go&p=$path&f=$filename" );
    exit();
}

sub upload_file {
    my ($q) = @_;

    my $path     = $q->param('p')    // q{};
    my $filename = $q->param('file') // q{};

    if ( !$filename ) {
        print $q->redirect( $BASE_URL . '?msg=file-required' );
        exit();
    }

    my $dontup = $conf->{page}->{dont_upload};
    my @dontup = split /[,]/, $dontup;
    my %dontup = ();
    foreach my $file_ext (@dontup) {
        $dontup{ lc $file_ext } = 1;
    }

    my @chunks = split( /[.]/, $filename );
    my $ext    = q{};
    if ( scalar @chunks > 1 ) {
        $ext = pop @chunks;
    }
    my $ext_lc = lc $ext;

    # check extension
    if ( exists $dontup{$ext_lc} ) {
        carp("Upload rejected due to disallowed file type: $ext\n");
        print $q->redirect( $BASE_URL . '?msg=rejected-file-type' );
        exit;
    }

    my $inputfh = $q->upload('file');
    if ( !$inputfh ) {
        carp("Failed to upload doc \"$filename\"\n");
        print $q->redirect( $BASE_URL . '?msg=upload-failed' );
        exit;
    }

    my $outfile = sprintf( '%s/%s/%s', $HTML_DIR, $path, $filename );
    if ( !copy( $inputfh, $outfile ) ) {
        carp("Failed to copy uploaded file to \"$outfile\": $!\n");
        print $q->redirect( $BASE_URL . '?msg=filecopy-failed' );
        exit;
    }

    print $q->redirect( $BASE_URL . "?do=go&p=$path&msg=success" );
    exit();
}

sub create_dir {
    my ($q) = @_;

    my $path    = $q->param('p')    // q{}; # relative path to current dir
    my $dirname = $q->param('name') // q{}; # new dir name

    if ( !$dirname ) {
        print $q->redirect( $BASE_URL . "?do=go&p=$path&msg=dirname-required" );
        exit();
    }
    elsif ( $dirname =~ /\W/ ) {
        print $q->redirect( $BASE_URL . "?do=go&p=$path&msg=english-letters-and-digits" );
        exit();
    }

    my $newpath = sprintf( '%s/%s', $path,     $dirname );
    my $dir     = sprintf( '%s/%s', $HTML_DIR, $newpath );
    if ( -d $dir ) {
        print $q->redirect( $BASE_URL . "?do=go&p=$path&msg=dir-exists" );
        exit();
    }

    my $rc = Utils::make_path(
        path => $dir,
    );

    print $q->redirect( $BASE_URL . "?do=go&p=$newpath" );
    exit();
}

sub delete_file {
    my ($q) = @_;

    my $path     = $q->param('p') // q{};
    my $filename = $q->param('f') // q{};

    my $file = sprintf( '%s/%s/%s', $HTML_DIR, $path, $filename );

    unlink($file);

    print $q->redirect( $BASE_URL . "?do=go&p=$path" );
    exit();
}

sub delete_dir {
    my ($q) = @_;

    my $path = $q->param('p') // q{};
    if ( !$path ) {
        print $q->redirect( $BASE_URL . "?do=go&p=$path&msg=root-dir" );
        exit();
    }

    my $parent_path = get_parent_path($path);

    my $dir = sprintf( '%s/%s', $HTML_DIR, $path );
    Utils::empty_dir_recurs( dir => $dir );
    rmdir($dir);

    print $q->redirect( $BASE_URL . "?do=go&p=$parent_path" );
    exit();
}

